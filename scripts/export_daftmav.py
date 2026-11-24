"""Write a confirmed plan into a copy of the DaftMav planner workbook."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

import openpyxl

from domain import survey_slot_capacity
from plan import Plan
from state_store import SystemSurvey


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = (
    SKILL_DIR
    / "references"
    / "Colonization Construction v3.4 (By DaftMav).xlsx"
)

SETTINGS_TAB_ROWS = range(18, 38)
COLONY_INPUT_ROWS = range(5, 506)
PRIMARY_ROW = 5


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value.lower())


def resolve_colony_tab(
    workbook: openpyxl.Workbook,
    system_name: str,
    requested_tab: str | None,
) -> str:
    settings = workbook["Settings"]
    if requested_tab:
        if requested_tab in workbook.sheetnames:
            return requested_tab
        raise ValueError(f"Colony tab {requested_tab!r} does not exist")

    for row in SETTINGS_TAB_ROWS:
        if settings.cell(row=row, column=3).value == system_name:
            tab_name = settings.cell(row=row, column=2).value
            if tab_name:
                return str(tab_name)

    for row in SETTINGS_TAB_ROWS:
        system_value = settings.cell(row=row, column=3).value
        if system_value in {None, "", "<System name here!>"}:
            tab_name = settings.cell(row=row, column=2).value
            if tab_name:
                return str(tab_name)

    raise ValueError("No empty Colony tab is available")


def _settings_row_for_tab(
    workbook: openpyxl.Workbook,
    tab_name: str,
) -> int:
    settings = workbook["Settings"]
    for row in SETTINGS_TAB_ROWS:
        if settings.cell(row=row, column=2).value == tab_name:
            return row
    raise ValueError(f"Colony tab {tab_name!r} is not registered in Settings")


def _clear_colony_inputs(
    worksheet: openpyxl.worksheet.worksheet.Worksheet,
) -> None:
    for row in COLONY_INPUT_ROWS:
        for column in range(1, 6):  # A:E
            worksheet.cell(row=row, column=column).value = None
        worksheet.cell(row=row, column=10).value = False  # J
        worksheet.cell(row=row, column=11).value = False  # K
        worksheet.cell(row=row, column=13).value = None  # M


def _write_settings(
    workbook: openpyxl.Workbook,
    tab_name: str,
    survey: SystemSurvey,
) -> None:
    settings = workbook["Settings"]
    row = _settings_row_for_tab(workbook, tab_name)
    settings.cell(row=row, column=2).value = tab_name
    settings.cell(row=row, column=3).value = survey.system_name
    settings.cell(row=row, column=4).value = survey_slot_capacity(
        survey,
        "orbital",
    )
    settings.cell(row=row, column=5).value = survey_slot_capacity(
        survey,
        "surface",
    )


def _write_constructions(
    worksheet: openpyxl.worksheet.worksheet.Worksheet,
    plan: Plan,
) -> None:
    for index, item in enumerate(plan.constructions):
        row = PRIMARY_ROW + index
        worksheet.cell(row=row, column=1).value = item.body_key
        worksheet.cell(row=row, column=2).value = (
            "Orbital" if item.slot == "orbital" else "Surface"
        )
        worksheet.cell(row=row, column=4).value = item.facility
        worksheet.cell(row=row, column=5).value = (
            f"Step {item.build_order} ({item.source_goal_id})"
        )
        worksheet.cell(row=row, column=10).value = False
        worksheet.cell(row=row, column=11).value = False
        worksheet.cell(row=row, column=13).value = item.layout_variant


def export_daftmav(
    survey: SystemSurvey,
    plan: Plan,
    *,
    output_path: Path,
    workbook_path: Path = DEFAULT_WORKBOOK,
    colony_tab: str | None = None,
) -> str:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workbook_path, output_path)
    workbook = openpyxl.load_workbook(output_path)
    tab_name = resolve_colony_tab(workbook, survey.system_name, colony_tab)
    worksheet = workbook[tab_name]

    _clear_colony_inputs(worksheet)
    _write_settings(workbook, tab_name, survey)
    _write_constructions(worksheet, plan)
    workbook.save(output_path)
    return tab_name


def render_ravencolonial_guide(
    survey: SystemSurvey,
    plan: Plan,
) -> str:
    lines: list[str] = []
    lines.append(f"# ravencolonial Entry Guide: {survey.system_name}")
    lines.append("")
    lines.append("RavenColonial requires manual entry. Use this order.")
    lines.append("")
    lines.append(f"1. Open the system: {survey.system_name}")
    lines.append("2. Confirm the body list matches the survey.")
    lines.append("3. Enter the primary port first.")
    lines.append("")
    lines.append("| Step | Body | Facility | Layout Variant | Slot |")
    lines.append("|---|---|---|---|---|")
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
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append(
        "Exact orbital and surface construction site counts must be confirmed "
        "in-game or in RavenColonial before finalizing."
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survey", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--workbook", type=Path, default=DEFAULT_WORKBOOK)
    parser.add_argument("--colony-tab", help="Optional Colony1..Colony20 target.")
    args = parser.parse_args()

    survey = SystemSurvey.from_dict(load_json(args.survey))
    plan = Plan.from_dict(load_json(args.plan))
    output_path = (
        args.output_dir
        / f"daftmav-{slugify(survey.system_name)}-{plan.plan_id}.xlsx"
    )
    tab_name = export_daftmav(
        survey,
        plan,
        output_path=output_path,
        workbook_path=args.workbook,
        colony_tab=args.colony_tab,
    )

    guide_path = args.output_dir / "ravencolonial.md"
    guide_path.write_text(
        render_ravencolonial_guide(survey, plan),
        encoding="utf-8",
    )

    print(f"Wrote {output_path}")
    print(f"Colony tab: {tab_name}")
    print(f"Wrote {guide_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
