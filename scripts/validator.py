"""Validate a concrete colonization plan."""

from __future__ import annotations

from typing import Any

from domain import (
    facility_location,
    is_station_structure,
    is_primary_facility,
    layout_options,
    point_effects,
    survey_body,
    survey_slot_capacity,
    structure_by_name,
)
from plan import Plan
from state_store import SystemSurvey


def _prerequisite_met(
    prerequisite: str,
    plan: Plan,
) -> bool:
    if not prerequisite or prerequisite == "Primary slot":
        return True
    return any(
        prerequisite == item.facility
        or prerequisite in item.facility
        or item.facility in prerequisite
        for item in plan.constructions
    )


def _station_ranks(
    plan: Plan,
    model: dict[str, Any],
) -> dict[int, int]:
    ranks: dict[int, int] = {}
    rank = 0
    for item in plan.constructions:
        if item.primary:
            continue
        if not is_station_structure(item.facility, model):
            continue
        rank += 1
        ranks[id(item)] = rank
    return ranks


def validate_plan(
    plan: Plan,
    survey: SystemSurvey,
    model: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    needs_more_input = False

    if not plan.constructions:
        return {
            "status": "invalid",
            "errors": ["plan has no constructions"],
            "warnings": [],
            "summary": {},
        }

    primary_items = [item for item in plan.constructions if item.primary]
    if len(primary_items) != 1:
        errors.append(
            f"exactly one primary construction is required, found {len(primary_items)}"
        )
    elif plan.constructions[0] != primary_items[0]:
        errors.append("primary construction must be the first build row")

    used_by_location: dict[str, int] = {"orbital": 0, "surface": 0}
    for item in plan.constructions:
        structure = structure_by_name(model, item.facility)
        if structure is None:
            errors.append(f"unknown facility: {item.facility}")
            continue

        expected_location = facility_location(structure["name"])
        if item.slot != expected_location:
            errors.append(
                f"{item.facility} is {expected_location}, "
                f"but construction row uses {item.slot}"
            )
        used_by_location[item.slot] += 1

        if item.primary and not is_primary_facility(structure["name"]):
            errors.append(
                f"primary construction uses non-primary facility {item.facility}"
            )
        if not item.primary and is_primary_facility(structure["name"]):
            errors.append(
                f"non-primary construction uses primary-only facility {item.facility}"
            )

        options = layout_options(model, structure["name"])
        if options:
            if item.layout_variant is None:
                errors.append(
                    f"{item.facility} requires a layout variant"
                )
            elif item.layout_variant not in {
                option["layout_variant"] for option in options
            }:
                errors.append(
                    f"layout variant {item.layout_variant!r} is invalid "
                    f"for {item.facility}"
                )

        prerequisite = structure.get("prerequisites")
        if prerequisite and prerequisite != "Primary slot":
            if not _prerequisite_met(prerequisite, plan):
                errors.append(
                    f"{item.facility} prerequisite not met: {prerequisite}"
                )

    for location in ("orbital", "surface"):
        available = survey_slot_capacity(survey, location)
        used = used_by_location[location]
        if available is None:
            if used:
                needs_more_input = True
                warnings.append(
                    f"{location} construction site count is unknown; "
                    f"cannot validate {used} used slot(s)"
                )
        elif available < used:
            errors.append(
                f"{location} slots used {used} exceeds available {available}"
            )

    t2_total = 0
    t3_total = 0
    station_ranks = _station_ranks(plan, model)
    for item in plan.constructions:
        structure = structure_by_name(model, item.facility)
        if structure is None:
            continue
        rank = station_ranks.get(id(item), 0)
        t2_effect, t3_effect = point_effects(
            structure,
            primary=item.primary,
            station_rank=rank,
            model=model,
        )
        t2_total += t2_effect
        t3_total += t3_effect

    if t2_total < 0:
        errors.append(f"T2 point total is negative: {t2_total}")
    if t3_total < 0:
        errors.append(f"T3 point total is negative: {t3_total}")

    status = "valid"
    if errors:
        status = "invalid"
    elif needs_more_input:
        status = "needs_more_input"

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "orbital_used": used_by_location["orbital"],
            "surface_used": used_by_location["surface"],
            "orbital_available": survey_slot_capacity(survey, "orbital"),
            "surface_available": survey_slot_capacity(survey, "surface"),
            "t2_total": t2_total,
            "t3_total": t3_total,
        },
    }
