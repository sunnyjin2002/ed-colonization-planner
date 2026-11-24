"""CLI wrapper for checking GoalStructureSet feasibility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from domain import load_model
from feasibility import check_feasibility
from goal_set import GoalStructureSet
from state_store import SystemSurvey


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True, type=Path)
    parser.add_argument("--goal-structure-set", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the feasibility JSON should be written.",
    )
    args = parser.parse_args()

    survey = SystemSurvey.from_dict(load_json(args.survey))
    goal_structure_set = GoalStructureSet.from_dict(
        load_json(args.goal_structure_set)
    )
    model = load_model()
    result = check_feasibility(goal_structure_set, survey, model)
    payload = result.to_dict()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    print(f"Feasibility: {payload['status']}")
    return 0 if payload["status"] == "feasible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
