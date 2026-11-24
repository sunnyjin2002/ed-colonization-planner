# Elite Dangerous Colonization Planner Skill

## Purpose

This skill helps players plan how to colonize an uninhabited system in Elite Dangerous.

It is designed to:

1. Fetch the target system's body layout from EDSM, with manual entry as a fallback.
2. Let the player correct or complete missing data, especially construction site counts and primary port placement.
3. Validate an explicit construction idea before building a full plan.
4. Suggest economy specializations and a development focus when the player has no fixed idea.
5. Generate, compare, and revise a colonization plan.
6. Export the confirmed plan to (a copy of) CMDR DaftMav's Conlonication Construction planner and produce ravencolonial entry guidance.

The skill is intentionally not responsible for in-game actions, reading the player's Frontier account, or guessing the exact construction site counts.

## Dialogue Flow

The intended interaction follows this state machine:

```text
IDLE
  -> SURVEYING
  -> GOAL_CAPTURE
  -> FEASIBILITY
  -> STRATEGY
  -> PLANNING
  -> REVIEW
  -> FINALIZED
  -> EXPORTED
```

`PLANNING -> REVIEW -> PLANNING` is the main revision loop.

### 1. Surveying

The player provides a system name.

The skill:

- calls the EDSM system and bodies APIs;
- falls back to an empty or partially manual survey;
- normalizes body data;
- returns an editable survey summary.

Example:

```text
System: Sol
Bodies: 12
Orbital site candidates: 8
Surface site candidates: 4
Missing:
  - exact orbital slots
  - exact surface slots
  - primary port location
```

The player can edit the survey through conversation updates or through the host application's frontend.

### 2. Goal Capture

If the player has a concrete idea, the skill converts it into a hard constraint.

Example:

```text
Player: Build a T3 starport at A3.
```

This becomes a structured goal instead of a vague instruction.

### 3. Feasibility

The skill validates the goal against colonization rules.

It returns:

```text
feasible
unmet constraints
required changes
explanation
```

Hard rules include:

- primary station placement;
- construction site availability;
- prerequisites;
- T2/T3 point requirements;
- layout variant compatibility.

### 4. Strategy

If the player has no explicit plan, the skill scores candidate bodies and proposes several strategies.

Each strategy includes:

- recommended development focus;
- recommended economy;
- advantages and risks;
- prerequisites;
- conflicts with player constraints.

Strategy suggestions are advisory and never override explicit player goals.

### 5. Planning and Review

The skill generates a versioned plan containing:

- selected constructions;
- build order;
- slot usage;
- T2/T3 points;
- score;
- economy effects;
- population effects;
- commodity totals;
- hauling trips.

The player can revise the plan. Each change creates a new plan version so older options remain comparable.

### 6. Export

After confirmation, the skill can export:

```text
Markdown
HTML
JSON
DaftMav xlsx copy
ravencolonial entry guide
```

When writing a DaftMav copy, only player input cells are modified:

```text
Settings:
  B18:B37  colony tab name
  C18:C37  system name
  D18:D37  orbital slots
  E18:E37  planetary slots

ColonyN:
  A  body
  B  slot
  D  facility
  E  notes
  J  build active
  K  build done
  M  layout variant
```

Formula columns are preserved.

## Usage

The intended invocation is:

```text
$ed-colonization-planner 规划 Sol 的殖民地
```

Example requests:

```text
$ed-colonization-planner 调查 Shinrarta Dezhra
$ed-colonization-planner 检查 A3 建 T3 空间站是否可行
$ed-colonization-planner 帮我建议这个星系适合发展什么经济
$ed-colonization-planner 根据当前方案生成 DaftMav Excel
```

The skill keeps user state outside the skill folder.

## State Storage

The skill uses a `StateStore` abstraction:

```text
MemoryStateStore       temporary, local process
TempFileStateStore     temporary, single machine
WorkspaceStateStore    current project workspace
DatabaseStateStore     multi-user web application
S3StateStore           generated files and attachments
```

The skill itself only reads and writes state through:

```text
get_state(conversation_id, key)
put_state(conversation_id, key, value)
delete_state(conversation_id, key)
```

The host decides which implementation to inject.

## Project Layout

```text
ed-colonization-planner/
  SKILL.md
  README.md
  references/
    workbook_map.md
    colonization_rules.md
    body_data_sources.md
    daftmav-planner-v3.4.xlsx
  assets/
    colonization_model.json
  scripts/
    extract_workbook.py
    fetch_system_bodies.py
    goal_set.py
    domain.py
    feasibility.py
    feasibility_cli.py
    strategy.py
    strategy_cli.py
    plan.py
    plan_cli.py
    validator.py
    validator_cli.py
    render_plan.py
    export_daftmav.py
    export_plan.py
```

This layout is the current implementation. Strategy references are still being
refined from external colonization guides.

## Tech Stack

Planned implementation:

```text
Python
openpyxl
FastAPI or host chatbot tool adapter
SQLAlchemy for multi-user persistence
EDSM system API
EDSM bodies API
JSON for plan state and static model
```

The Excel workbook is treated as an upstream data source and export target, not as the runtime calculation engine.

## Disclaimer
- This project is not affiliated with Frontier Developments. Elite Dangerous is a trademark of Frontier Developments plc.