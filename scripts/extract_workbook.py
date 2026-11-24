"""Extract the static colonization model from the DaftMav workbook.

The source workbook is treated as the upstream data authority. This script
reads its cached values and writes a machine-readable JSON model that the
planner can consume without requiring Excel or a recalculation engine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openpyxl


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = (
    SKILL_DIR
    / "references"
    / "Colonization Construction v3.4 (By DaftMav).xlsx"
)
DEFAULT_OUTPUT = SKILL_DIR / "assets" / "colonization_model.json"


def _clean(value: Any) -> Any:
    """Convert spreadsheet values to JSON-friendly Python values."""
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        return stripped
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _to_number(value: Any) -> int | float | None:
    """Parse numeric cells, including comma-formatted text values."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if cleaned == "":
            return None
        try:
            number = float(cleaned)
        except ValueError:
            return None
        return int(number) if number.is_integer() else number
    return None


def _cell(
    worksheet: openpyxl.worksheet.worksheet.Worksheet,
    row: int,
    column: int,
) -> Any:
    return _clean(worksheet.cell(row=row, column=column).value)


def _extract_defaults(workbook: openpyxl.Workbook) -> dict[str, Any]:
    settings = workbook["Settings"]
    return {
        "min_supply_volume": _to_number(_cell(settings, 4, 3)),
        "max_system_distance_ly": _to_number(_cell(settings, 5, 3)),
        "max_station_distance_ls": _to_number(_cell(settings, 6, 3)),
        "market_last_updated_days": _to_number(_cell(settings, 7, 3)),
        "large_ship_cargo": _to_number(_cell(settings, 4, 6)),
        "medium_ship_cargo": _to_number(_cell(settings, 5, 6)),
        "carrier_cargo": _to_number(_cell(settings, 6, 6)),
    }


def _extract_station_cost_modifiers(
    workbook: openpyxl.Workbook,
) -> list[dict[str, Any]]:
    lists = workbook["Lists"]
    modifiers: list[dict[str, Any]] = []
    for row in range(3, 14):
        structure = _cell(lists, row, 1)
        if not structure:
            continue
        if structure == "TBA":
            modifiers.append(
                {
                    "structure": structure,
                    "extra_t2_cost": None,
                    "extra_t3_cost": None,
                }
            )
            continue
        modifiers.append(
            {
                "structure": structure,
                "extra_t2_cost": _to_number(_cell(lists, row, 2)),
                "extra_t3_cost": _to_number(_cell(lists, row, 3)),
            }
        )
    return modifiers


def _extract_initial_station_regex(
    workbook: openpyxl.Workbook,
) -> list[dict[str, Any]]:
    lists = workbook["Lists"]
    result: list[dict[str, Any]] = []
    for row in range(16, 22):
        pattern = _cell(lists, row, 1)
        if not pattern:
            continue
        result.append(
            {
                "pattern": pattern,
                "percentage_increase": _to_number(_cell(lists, row, 2)),
            }
        )
    return result


def _extract_structures(workbook: openpyxl.Workbook) -> list[dict[str, Any]]:
    stats = workbook["Stats"]
    structures: list[dict[str, Any]] = []
    for row in range(2, 76):
        name = _cell(stats, row, 1)
        if not name:
            continue
        structures.append(
            {
                "name": name,
                "max_pad": _cell(stats, row, 2),
                "prerequisites": _cell(stats, row, 3),
                "system_unlock": _cell(stats, row, 4),
                "strong_link_unlock": _cell(stats, row, 5),
                "t2": _to_number(_cell(stats, row, 6)),
                "t3": _to_number(_cell(stats, row, 7)),
                "security": _to_number(_cell(stats, row, 9)),
                "tech_level": _to_number(_cell(stats, row, 10)),
                "wealth": _to_number(_cell(stats, row, 11)),
                "standard_of_living": _to_number(_cell(stats, row, 12)),
                "development_level": _to_number(_cell(stats, row, 13)),
                "facility_economy": _cell(stats, row, 14),
                "economy_influence": _cell(stats, row, 15),
                "init_pop_inc": _to_number(_cell(stats, row, 16)),
                "max_pop_inc": _to_number(_cell(stats, row, 17)),
            }
        )
    return structures


def _extract_layouts(workbook: openpyxl.Workbook) -> list[dict[str, Any]]:
    lists = workbook["Lists"]
    layouts: list[dict[str, Any]] = []
    for row in range(48, 211):
        structure = _cell(lists, row, 1)
        if not structure:
            continue
        layouts.append(
            {
                "structure": structure,
                "layout_variant": _cell(lists, row, 2),
                "max_landing_pad": _cell(lists, row, 3),
                "score": _to_number(_cell(lists, row, 4)),
                "influence": _cell(lists, row, 5),
                "max_population": _to_number(_cell(lists, row, 6)),
                "orbital_surface": _cell(lists, row, 7),
                "type": _cell(lists, row, 8),
                "reported_bugs": _cell(lists, row, 9),
                "settlement_size": _cell(lists, row, 10),
                "observed_pop_inc_min": _to_number(_cell(lists, row, 11)),
                "observed_pop_inc_max": _to_number(_cell(lists, row, 12)),
            }
        )
    return layouts


def _extract_commodities(workbook: openpyxl.Workbook) -> list[dict[str, Any]]:
    commodities_sheet = workbook["Commodities"]

    normal_structures = [
        _cell(commodities_sheet, 1, column)
        for column in range(16, 90)
        if _cell(commodities_sheet, 1, column)
    ]
    primary_structures = [
        _cell(commodities_sheet, 1, column)
        for column in range(91, 102)
        if _cell(commodities_sheet, 1, column)
    ]
    commodities: list[dict[str, Any]] = []
    current_category: str | None = None

    for row in range(9, 75):
        category_header = _cell(commodities_sheet, row, 4)
        if category_header:
            current_category = category_header
            continue

        commodity_name = _cell(commodities_sheet, row, 5)
        if not commodity_name:
            continue

        structure_requirements: dict[str, int | float | None] = {}
        for column_index, structure_name in enumerate(normal_structures, start=16):
            if structure_name is not None:
                structure_requirements[str(structure_name)] = _to_number(
                    _cell(commodities_sheet, row, column_index)
                )
        for column_index, structure_name in enumerate(primary_structures, start=91):
            if structure_name is not None:
                structure_requirements[str(structure_name)] = _to_number(
                    _cell(commodities_sheet, row, column_index)
                )

        commodities.append(
            {
                "name": commodity_name,
                "inara_id": _to_number(_cell(commodities_sheet, row, 2)),
                "internal_key": _cell(commodities_sheet, row, 3),
                "category": current_category,
                "produced_by": _cell(commodities_sheet, row, 6),
                "consumed_by": _cell(commodities_sheet, row, 7),
                "structure_requirements": structure_requirements,
            }
        )

    return commodities


def _extract_source_info(
    workbook: openpyxl.Workbook,
    workbook_path: Path,
) -> dict[str, Any]:
    changelog = workbook["Changelog"]
    digest = hashlib.sha256(workbook_path.read_bytes()).hexdigest()
    return {
        "workbook_filename": workbook_path.name,
        "workbook_sha256": digest,
        "workbook_version": _to_number(_cell(changelog, 4, 4)),
        "lists_data_version": _to_number(_cell(changelog, 5, 4)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_model(workbook_path: Path) -> dict[str, Any]:
    workbook = openpyxl.load_workbook(workbook_path, data_only=True)
    return {
        "schema_version": "1.0",
        "source": _extract_source_info(workbook, workbook_path),
        "defaults": _extract_defaults(workbook),
        "station_cost_modifiers": _extract_station_cost_modifiers(workbook),
        "initial_station_regex": _extract_initial_station_regex(workbook),
        "structures": _extract_structures(workbook),
        "structure_layouts": _extract_layouts(workbook),
        "commodities": _extract_commodities(workbook),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_WORKBOOK,
        help="Path to the DaftMav xlsx file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Path where the generated JSON model should be written.",
    )
    args = parser.parse_args()

    model = build_model(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(model, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    print(f"Structures: {len(model['structures'])}")
    print(f"Layouts: {len(model['structure_layouts'])}")
    print(f"Commodities: {len(model['commodities'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
