"""CLI wrapper for validating an existing plan JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from domain import load_model
from plan import Plan
from state_store import SystemSurvey
from validator import validate_plan


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where validation JSON should be written.",
    )
    args = parser.parse_args()

    survey = SystemSurvey.from_dict(load_json(args.survey))
    plan = Plan.from_dict(load_json(args.plan))
    model = load_model()
    validation = validate_plan(plan, survey, model)
    payload = json.dumps(validation, ensure_ascii=False, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(payload)
    print(f"Validation: {validation['status']}")
    return 0 if validation["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
