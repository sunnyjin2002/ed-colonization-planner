---
name: ed-colonization-planner
description: Plan Elite Dangerous system colonization when the user wants to survey a system, validate a construction idea, choose an economy strategy, generate a build plan, or export a DaftMav/ravencolonial plan.
---

# Elite Dangerous Colonization Planner

Plan and validate Elite Dangerous colonization goals. Use this skill when the
user wants to:

- research a system for colonization;
- check whether a specific construction idea is feasible;
- choose a development focus or economy strategy;
- generate a concrete construction plan;
- export a plan to DaftMav or ravencolonial.

Do not use this skill for general Elite Dangerous lore or translation work.

## Important Boundaries

- Do not guess exact orbital/surface construction site counts. They must come
  from the player.
- Do not write user state into the skill folder.
- Do not modify the original DaftMav workbook. Export a copy.
- EDSM body labels are best-effort. The player's in-game body name is
  authoritative.

## State

Use a `StateStore` implementation provided by the host:

```text
get_state(conversation_id, key)
put_state(conversation_id, key, value)
```

Store:

```text
SystemSurvey
StrategyIntent
GoalStructureSet
Plan versions
```

Do not store this state in the skill directory.

## Core Workflow

```text
SURVEYING
  -> GOAL_CAPTURE
  -> FEASIBILITY
  -> STRATEGY
  -> PLANNING
  -> REVIEW
  -> FINALIZED
  -> EXPORTED
```

The main revision loop is:

```text
PLANNING -> REVIEW -> PLANNING
```

## 1. Survey the System

Ask for the system name if it is missing.

Run:

```bash
python scripts/fetch_system_bodies.py --system "<system name>"
```

This uses EDSM and returns an editable `SystemSurvey`.

If EDSM has no data, create an empty manual survey and ask the player for the
body list.

Always mark missing fields:

- exact orbital construction sites
- exact surface construction sites
- primary port body

## 2. Capture Goals

If the player gives a concrete construction idea, convert it directly into a
`GoalStructureSet`.

If the player gives a high-level strategic or economic intent, first create a
`StrategyIntent`, then retrieve relevant guide knowledge and propose candidate
`GoalStructureSet` options. Let the player select or modify one.

Example 1:

```text
Player: I want to build a T3 starport at A3.
```

Example 2:

```text
Player: I want to build a strong extraction economy.
```

Example 3:

```text
Player: I want to build a starport at the ELW, and make it's economy strong.
```

Handle each case differently:

```text
Example 1:
  Create GoalStructureSet directly.

Example 2:
  Create StrategyIntent.
  Retrieve relevant guide knowledge.
  Propose candidate GoalStructureSet options.

Example 3:
  Create a mixed intent:
    - concrete goal: primary/starport at the ELW
    - StrategyIntent: strengthen economy
  Generate candidate GoalStructureSet options that preserve the concrete
  constraint.
```

Do not generate a complete plan yet.

## 3. Check Feasibility

Run the feasibility tool against the current `GoalStructureSet` and
`SystemSurvey`.

```bash
python scripts/feasibility_cli.py \
  --survey state/survey.json \
  --goal-structure-set state/goal_structure_set.json \
  --output state/feasibility.json
```

Explain the result:

- `feasible`
- `infeasible`
- `needs_more_input`

If infeasible, report unmet constraints and ask the player to revise the goal
or add missing information.

## 4. Suggest Strategies

If the player has no clear goal, run:

```bash
python scripts/strategy_cli.py \
  --survey state/survey.json \
  --output state/strategy_options.json
```

Present 2-3 candidate strategies, explain the trade-offs, and let the player
select one. The selected strategy becomes the `GoalStructureSet`.

Strategy suggestions are advisory. They never override explicit player goals.

## 5. Generate a Plan

After the `GoalStructureSet` is feasible, run:

```bash
python scripts/plan_cli.py \
  --survey state/survey.json \
  --goal-structure-set state/goal_structure_set.json \
  --plan-id colony-plan-v1 \
  --output state/plan.json
```

`plan.py` resolves abstract goals into:

- concrete facility
- layout variant
- orbital/surface slot
- body assignment
- primary-first build order

## 6. Validate the Plan

Run:

```bash
python scripts/validator_cli.py \
  --survey state/survey.json \
  --plan state/plan.json \
  --output state/validation.json
```

Report validation errors and warnings.

Do not export an invalid plan.

## 7. Discuss and Revise

Show the plan summary, slot usage, T2/T3 points, and validation status.

Allow the player to:

- change body assignment;
- change facility or layout;
- change primary port;
- add or remove support facilities;
- change economy strategy.

Each revision should create a new plan version.

## 8. Export

After the player confirms the plan, run:

```bash
python scripts/export_plan.py \
  --survey state/survey.json \
  --goal-structure-set state/goal_structure_set.json \
  --plan-id colony-plan-v1 \
  --output-dir output
```

This writes:

```text
output/plan.json
output/daftmav.xlsx
output/ravencolonial.md
```

Ask the player which `Colony1..Colony20` tab to use if it is not clear.

For Markdown/HTML preview only, use:

```bash
python scripts/render_plan.py \
  --survey state/survey.json \
  --plan state/plan.json \
  --output-dir output \
  --formats json,markdown,html
```

## Scripts

| Script | Purpose |
|---|---|
| `extract_workbook.py` | Regenerate `colonization_model.json` from the DaftMav xlsx |
| `fetch_system_bodies.py` | Fetch EDSM system and body data |
| `state_store.py` | Conversation-scoped state models and adapters |
| `feasibility.py` | Early feasibility checks for a `GoalStructureSet` |
| `feasibility_cli.py` | CLI for feasibility checks |
| `strategy.py` | Generate candidate `GoalStructureSet` options |
| `strategy_cli.py` | CLI for strategy generation |
| `plan.py` | Materialize a `GoalStructureSet` into a concrete plan |
| `plan_cli.py` | CLI for plan generation |
| `validator.py` | Validate a concrete plan |
| `validator_cli.py` | CLI for plan validation |
| `render_plan.py` | Render Markdown, HTML, and JSON |
| `export_daftmav.py` | Export a DaftMav copy and ravencolonial guide |
| `export_plan.py` | End-to-end feasibility, plan, validation, and export |

## Rules

Hard construction rules are encoded in:

```text
assets/colonization_model.json
scripts/domain.py
scripts/feasibility.py
scripts/validator.py
```

Do not recalculate these rules in the prompt. Use the scripts.

When deeper strategy or conceptual guidance is needed, read the relevant
`references/` file or use the host RAG system. Do not rely on model memory for
colonization mechanics.
