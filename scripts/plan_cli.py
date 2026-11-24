"""CLI wrapper for generating and validating a concrete plan."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from domain import load_model
from goal_set import GoalStructureSet
from plan import generate_plan
from state_store import SystemSurvey
from validator import validate_plan


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True, type=Path)
    parser.add_argument("--goal-structure-set", required=True, type=Path)
    parser.add_argument("--plan-id", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--version",
        type=int,
        default=1,
        help="Plan version number.",
    )
    args = parser.parse_args()

    survey = SystemSurvey.from_dict(load_json(args.survey))
    goal_structure_set = GoalStructureSet.from_dict(
        load_json(args.goal_structure_set)
    )
    model = load_model()
    plan = generate_plan(
        goal_structure_set,
        survey,
        model,
        plan_id=args.plan_id,
        version=args.version,
    )
    validation = validate_plan(plan, survey, model)
    plan.validation_result = validation
    plan.status = validation["status"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(plan.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    print(f"Plan status: {plan.status}")
    if validation["errors"]:
        for error in validation["errors"]:
            print(f"Error: {error}")
    return 0 if validation["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
