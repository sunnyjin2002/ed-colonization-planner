"""Render a colony survey and plan as JSON, Markdown, or HTML."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from domain import load_model
from plan import Plan
from state_store import SystemSurvey
from validator import validate_plan


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_render_context(
    survey_path: Path,
    plan_path: Path,
) -> tuple[SystemSurvey, Plan, dict[str, Any]]:
    survey = SystemSurvey.from_dict(load_json(survey_path))
    plan = Plan.from_dict(load_json(plan_path))
    model = load_model()
    validation = validate_plan(plan, survey, model)
    plan.validation_result = validation
    return survey, plan, validation


def _population_label(survey: SystemSurvey) -> str:
    known = survey.raw_system_data.get("population_known")
    if known is True:
        return "known"
    if known is False:
        return "uninhabited or unknown"
    return "unknown"


def render_markdown(
    survey: SystemSurvey,
    plan: Plan,
    validation: dict[str, Any],
) -> str:
    lines: list[str] = []
    lines.append(f"# Colonization Plan: {survey.system_name}")
    lines.append("")
    lines.append(f"- Provider: {survey.provider or 'manual'}")
    lines.append(f"- Population: {_population_label(survey)}")
    lines.append(f"- Plan: {plan.plan_id} v{plan.version}")
    lines.append(f"- Status: {plan.status}")
    lines.append("")

    missing = ", ".join(survey.missing_fields) or "none"
    lines.append(f"Missing survey fields: {missing}")
    lines.append("")

    lines.append("## Validation")
    lines.append("")
    lines.append(f"- Status: {validation['status']}")
    for error in validation["errors"]:
        lines.append(f"- Error: {error}")
    for warning in validation["warnings"]:
        lines.append(f"- Warning: {warning}")
    lines.append("")

    lines.append("## Bodies")
    lines.append("")
    lines.append("| Key | Name | Type | Subtype | Landable | Orbital | Surface |")
    lines.append("|---|---|---|---|---|---|---|")
    for body in survey.bodies:
        lines.append(
            "| "
            + " | ".join(
                [
                    body.body_key or "",
                    body.name or "",
                    body.body_type or "",
                    body.sub_type or "",
                    "yes" if body.is_landable else ("no" if body.is_landable is False else ""),
                    str(body.orbital_site_candidates or ""),
                    str(body.surface_site_candidates or ""),
                ]
            )
            + " |"
        )
    lines.append("")

    lines.append("## Construction Plan")
    lines.append("")
    lines.append("| # | Body | Facility | Layout | Slot | Primary |")
    lines.append("|---|---|---|---|---|---|")
    for item in plan.constructions:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.build_order),
                    item.body_key,
                    item.facility,
                    item.layout_variant or "",
                    item.slot,
                    "yes" if item.primary else "no",
                ]
            )
            + " |"
        )
    lines.append("")

    summary = validation.get("summary", {})
    lines.append("## Summary")
    lines.append("")
    lines.append(
        "| Orbital Used | Surface Used | T2 | T3 |"
    )
    lines.append("|---|---|---|---|")
    lines.append(
        "| "
        + " | ".join(
            [
                str(summary.get("orbital_used", "")),
                str(summary.get("surface_used", "")),
                str(summary.get("t2_total", "")),
                str(summary.get("t3_total", "")),
            ]
        )
        + " |"
    )
    lines.append("")

    return "\n".join(lines)


def render_html(
    survey: SystemSurvey,
    plan: Plan,
    validation: dict[str, Any],
) -> str:
    body_rows = []
    for body in survey.bodies:
        body_rows.append(
            "<tr>"
            + "".join(
                [
                    f"<td>{html.escape(str(value))}</td>"
                    for value in [
                        body.body_key,
                        body.name,
                        body.body_type,
                        body.sub_type,
                        "yes" if body.is_landable else ("no" if body.is_landable is False else ""),
                        body.orbital_site_candidates or "",
                        body.surface_site_candidates or "",
                    ]
                ]
            )
            + "</tr>"
        )

    plan_rows = []
    for item in plan.constructions:
        plan_rows.append(
            "<tr>"
            + "".join(
                [
                    f"<td>{html.escape(str(value))}</td>"
                    for value in [
                        item.build_order,
                        item.body_key,
                        item.facility,
                        item.layout_variant or "",
                        item.slot,
                        "yes" if item.primary else "no",
                    ]
                ]
            )
            + "</tr>"
        )

    errors = "".join(
        f"<li>{html.escape(error)}</li>" for error in validation["errors"]
    )
    warnings = "".join(
        f"<li>{html.escape(warning)}</li>" for warning in validation["warnings"]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Colonization Plan: {html.escape(survey.system_name)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #222; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.45rem; text-align: left; }}
    th {{ background: #f4f4f4; }}
  </style>
</head>
<body>
  <h1>Colonization Plan: {html.escape(survey.system_name)}</h1>
  <p>Provider: {html.escape(survey.provider or 'manual')}</p>
  <p>Population: {html.escape(_population_label(survey))}</p>
  <p>Plan: {html.escape(plan.plan_id)} v{plan.version}</p>
  <h2>Validation</h2>
  <p>Status: {html.escape(validation['status'])}</p>
  <ul>{errors}{warnings}</ul>
  <h2>Bodies</h2>
  <table>
    <thead><tr><th>Key</th><th>Name</th><th>Type</th><th>Subtype</th><th>Landable</th><th>Orbital</th><th>Surface</th></tr></thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
  <h2>Construction Plan</h2>
  <table>
    <thead><tr><th>#</th><th>Body</th><th>Facility</th><th>Layout</th><th>Slot</th><th>Primary</th></tr></thead>
    <tbody>{''.join(plan_rows)}</tbody>
  </table>
</body>
</html>"""


def render_json(
    survey: SystemSurvey,
    plan: Plan,
    validation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "survey": survey.to_dict(),
        "plan": plan.to_dict(),
        "validation": validation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument(
        "--formats",
        default="json,markdown,html",
        help="Comma-separated output formats.",
    )
    args = parser.parse_args()

    survey, plan, validation = build_render_context(args.survey, args.plan)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    formats = {item.strip().lower() for item in args.formats.split(",")}

    outputs: list[Path] = []
    if "json" in formats:
        path = args.output_dir / "plan.json"
        path.write_text(
            json.dumps(render_json(survey, plan, validation), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        outputs.append(path)
    if "markdown" in formats or "md" in formats:
        path = args.output_dir / "plan.md"
        path.write_text(render_markdown(survey, plan, validation), encoding="utf-8")
        outputs.append(path)
    if "html" in formats:
        path = args.output_dir / "plan.html"
        path.write_text(render_html(survey, plan, validation), encoding="utf-8")
        outputs.append(path)

    for output in outputs:
        print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
