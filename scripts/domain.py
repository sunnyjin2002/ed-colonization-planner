"""Shared domain helpers for the colonisation planner."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from goal_set import Goal
from state_store import BodySurvey, SystemSurvey


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = SKILL_DIR / "assets" / "colonization_model.json"


@lru_cache(maxsize=1)
def load_model(path: str | Path | None = None) -> dict[str, Any]:
    model_path = Path(path) if path else DEFAULT_MODEL_PATH
    return json.loads(model_path.read_text(encoding="utf-8"))


def structure_by_name(
    model: dict[str, Any],
    name: str,
) -> dict[str, Any] | None:
    return next(
        (item for item in model["structures"] if item["name"] == name),
        None,
    )


def is_primary_facility(name: str) -> bool:
    return name.endswith("(Primary)")


def facility_location(name: str) -> str:
    if name.startswith("Orbital"):
        return "orbital"
    if name.startswith("Surface"):
        return "surface"
    return "unknown"


def facility_kind(name: str) -> str:
    if "- Starport -" in name:
        return "starport"
    if "- Outpost -" in name:
        return "outpost"
    if "- Installation -" in name:
        return "installation"
    if "- Planetary Port -" in name:
        return "planetary_port"
    if "- Settlement -" in name:
        return "settlement"
    if "- Hub -" in name:
        return "hub"
    return "unknown"


def matching_facilities(
    model: dict[str, Any],
    goal: Goal,
) -> list[dict[str, Any]]:
    if goal.facility:
        structure = structure_by_name(model, goal.facility)
        return [structure] if structure else []

    result: list[dict[str, Any]] = []
    for structure in model["structures"]:
        name = structure["name"]
        if goal.primary and not is_primary_facility(name):
            continue
        if goal.facility_class:
            if facility_kind(name) != goal.facility_class:
                continue
        if goal.tier is not None:
            if goal.tier == 3:
                if facility_kind(name) not in {"starport", "planetary_port"}:
                    continue
            elif goal.tier == 2:
                if "T2" not in name and facility_kind(name) not in {"outpost", "hub"}:
                    continue
            elif goal.tier == 1:
                if "T1" not in name and facility_kind(name) not in {"settlement", "installation"}:
                    continue
        result.append(structure)
    return result


def body_slot_capacity(
    body: BodySurvey,
    location: str,
) -> int | None:
    if location == "orbital":
        if body.manual_orbital_sites is not None:
            return body.manual_orbital_sites
        return body.orbital_site_candidates
    if location == "surface":
        if body.manual_surface_sites is not None:
            return body.manual_surface_sites
        return body.surface_site_candidates
    return None


def survey_slot_capacity(
    survey: SystemSurvey,
    location: str,
    body_key: str | None = None,
) -> int | None:
    total: int | None = 0
    for body in survey.bodies:
        if body_key is not None and body.body_key != body_key:
            continue
        capacity = body_slot_capacity(body, location)
        if capacity is None:
            return None
        total += capacity
    return total


def survey_body(
    survey: SystemSurvey,
    body_key: str,
) -> BodySurvey | None:
    return next(
        (body for body in survey.bodies if body.body_key == body_key),
        None,
    )


def is_station_structure(
    structure_name: str,
    model: dict[str, Any],
) -> bool:
    return any(
        item["structure"] == structure_name
        for item in model["station_cost_modifiers"]
    )


def station_extra_cost(
    structure_name: str,
    model: dict[str, Any],
    point_type: str,
) -> int | float:
    key = f"extra_{point_type}_cost"
    for item in model["station_cost_modifiers"]:
        if item["structure"] == structure_name:
            return item.get(key) or 0
    return 0


def point_cost(
    structure: dict[str, Any],
    primary: bool = False,
) -> tuple[int | float, int | float]:
    """Return required T2 and T3 point costs for a structure.

    Primary facilities do not consume construction points.
    """
    if primary:
        return 0, 0
    return (
        max(0, -(structure.get("t2") or 0)),
        max(0, -(structure.get("t3") or 0)),
    )


def point_income(structure: dict[str, Any]) -> tuple[int, int]:
    """Return positive T2 and T3 point contributions for a structure."""
    return (
        max(0, structure.get("t2") or 0),
        max(0, structure.get("t3") or 0),
    )


def point_effects(
    structure: dict[str, Any],
    *,
    primary: bool,
    station_rank: int,
    model: dict[str, Any],
) -> tuple[int | float, int | float]:
    """Return final T2/T3 contribution for a construction row.

    Primary facilities generate positive points but never consume points.
    Non-primary stations receive the DaftMav station-count price increase
    starting with the third non-primary station in the system.
    """
    t2 = structure.get("t2") or 0
    t3 = structure.get("t3") or 0
    if primary:
        return max(0, t2), max(0, t3)

    def adjusted(stat: int | float, point_type: str) -> int | float:
        if stat >= 0:
            return stat
        if (
            station_rank > 2
            and is_station_structure(structure["name"], model)
        ):
            extra = station_extra_cost(structure["name"], model, point_type)
            result = stat + ((station_rank - 2) * extra)
        else:
            result = stat
        if point_type == "t2":
            # The source workbook wraps the T2 calculation in ROUNDDOWN.
            return int(result)
        return result

    return adjusted(t2, "t2"), adjusted(t3, "t3")


def layout_options(
    model: dict[str, Any],
    structure_name: str,
) -> list[dict[str, Any]]:
    return [
        item
        for item in model["structure_layouts"]
        if item["structure"] == structure_name
    ]
