"""End-to-end export orchestration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from domain import load_model
from export_daftmav import export_daftmav, render_ravencolonial_guide
from feasibility import check_feasibility
from goal_set import GoalStructureSet
from plan import generate_plan
from render_plan import render_json
from state_store import SystemSurvey
from validator import validate_plan


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True, type=Path)
    parser.add_argument("--goal-structure-set", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--colony-tab")
    parser.add_argument(
        "--skip-feasibility",
        action="store_true",
        help="Generate and export even when feasibility is not clean.",
    )
    args = parser.parse_args()

    survey = SystemSurvey.from_dict(load_json(args.survey))
    goal_structure_set = GoalStructureSet.from_dict(
        load_json(args.goal_structure_set)
    )
    model = load_model()
    feasibility = check_feasibility(goal_structure_set, survey, model)
    if feasibility.status != "feasible" and not args.skip_feasibility:
        print(f"Feasibility is {feasibility.status}. Aborting export.")
        print(json.dumps(feasibility.to_dict(), ensure_ascii=False, indent=2))
        return 1

    plan = generate_plan(
        goal_structure_set,
        survey,
        model,
        plan_id=args.plan_id,
    )
    validation = validate_plan(plan, survey, model)
    plan.validation_result = validation
    plan.status = validation["status"]

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "plan.json").write_text(
        json.dumps(render_json(survey, plan, validation), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    tab_name = export_daftmav(
        survey,
        plan,
        output_path=args.output_dir / "daftmav.xlsx",
        colony_tab=args.colony_tab,
    )
    (args.output_dir / "ravencolonial.md").write_text(
        render_ravencolonial_guide(survey, plan),
        encoding="utf-8",
    )

    print(f"Wrote {args.output_dir}")
    print(f"Colony tab: {tab_name}")
    print(f"Plan status: {plan.status}")
    return 0 if plan.status == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
