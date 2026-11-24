"""Early-stage feasibility checks for a GoalStructureSet."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from domain import (
    body_slot_capacity,
    facility_location,
    is_primary_facility,
    is_station_structure,
    matching_facilities,
    point_cost,
    point_effects,
    point_income,
    survey_body,
    survey_slot_capacity,
)
from goal_set import GoalStructureSet
from state_store import SystemSurvey


@dataclass
class GoalFeasibility:
    goal_id: str
    status: str = "feasible"
    unmet_constraints: list[str] = field(default_factory=list)
    required_changes: list[str] = field(default_factory=list)


@dataclass
class FeasibilityResult:
    status: str
    goal_results: list[GoalFeasibility]
    unmet_constraints: list[str] = field(default_factory=list)
    point_budget: dict[str, Any] = field(default_factory=dict)
    explanation: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "goal_results": [
                {
                    "goal_id": item.goal_id,
                    "status": item.status,
                    "unmet_constraints": item.unmet_constraints,
                    "required_changes": item.required_changes,
                }
                for item in self.goal_results
            ],
            "unmet_constraints": self.unmet_constraints,
            "point_budget": self.point_budget,
            "explanation": self.explanation,
        }


def _prerequisite_satisfied(
    prerequisite: str,
    goal_structure_set: GoalStructureSet,
    model: dict[str, Any],
) -> bool:
    if not prerequisite:
        return True
    candidate_names: set[str] = set()
    for goal in goal_structure_set.goals:
        if goal.facility:
            candidate_names.add(goal.facility)
        else:
            candidate_names.update(
                item["name"] for item in matching_facilities(model, goal)
            )
    return any(
        prerequisite == name
        or prerequisite in name
        or name in prerequisite
        for name in candidate_names
    )


def _max_point_generation(
    model: dict[str, Any],
    location: str,
) -> tuple[int, int]:
    max_t2 = 0
    max_t3 = 0
    for structure in model["structures"]:
        if is_primary_facility(structure["name"]):
            continue
        if facility_location(structure["name"]) != location:
            continue
        t2_income, t3_income = point_income(structure)
        max_t2 = max(max_t2, t2_income)
        max_t3 = max(max_t3, t3_income)
    return max_t2, max_t3


def check_feasibility(
    goal_structure_set: GoalStructureSet,
    survey: SystemSurvey,
    model: dict[str, Any],
) -> FeasibilityResult:
    goal_results: list[GoalFeasibility] = []
    unmet: list[str] = []
    needs_more_input = False
    any_infeasible = False

    primary_count = 0
    for goal in goal_structure_set.goals:
        item = GoalFeasibility(goal.goal_id)
        body = survey_body(survey, goal.body_key)
        candidates = matching_facilities(model, goal)

        if body is None:
            item.status = "infeasible"
            item.unmet_constraints.append(
                f"body {goal.body_key} is not present in the survey"
            )

        if not candidates:
            item.status = "infeasible"
            item.unmet_constraints.append(
                f"no facility matches goal {goal.goal_id}"
            )

        if goal.primary:
            primary_count += goal.count
            if candidates and any(
                not is_primary_facility(candidate["name"])
                for candidate in candidates
            ):
                item.status = "infeasible"
                item.unmet_constraints.append(
                    "primary goal must use a (Primary) facility"
                )
            if candidates and any(
                facility_location(candidate["name"]) != "orbital"
                for candidate in candidates
            ):
                item.status = "infeasible"
                item.unmet_constraints.append(
                    "primary station must be an orbital facility"
                )
        elif candidates and any(
            is_primary_facility(candidate["name"])
            for candidate in candidates
        ):
            item.status = "infeasible"
            item.unmet_constraints.append(
                "non-primary goal cannot use a (Primary) facility"
            )

        if body is not None and candidates:
            location = facility_location(candidates[0]["name"])
            capacity = body_slot_capacity(body, location)
            if capacity is not None and capacity < goal.count:
                item.status = "infeasible"
                item.unmet_constraints.append(
                    f"{goal.body_key} has only {capacity} {location} slot(s), "
                    f"but goal requires {goal.count}"
                )
            elif capacity is None:
                item.status = "needs_more_input"
                item.unmet_constraints.append(
                    f"{goal.body_key} {location} construction site count is unknown"
                )

        if candidates:
            prerequisite = candidates[0].get("prerequisites")
            if prerequisite and prerequisite != "Primary slot":
                if not _prerequisite_satisfied(prerequisite, goal_structure_set, model):
                    item.status = "needs_more_input"
                    item.unmet_constraints.append(
                        f"prerequisite is not represented in GoalStructureSet: {prerequisite}"
                    )

        if item.status != "feasible":
            any_infeasible = any_infeasible or item.status == "infeasible"
            needs_more_input = needs_more_input or item.status == "needs_more_input"
        goal_results.append(item)

    if primary_count > 1:
        unmet.append("only one primary station is allowed")

    # Aggregate slot usage and point-capacity estimate.
    used_by_location: dict[str, int] = {"orbital": 0, "surface": 0}
    total_t2_effect = 0.0
    total_t3_effect = 0.0
    total_t2_cost = 0.0
    total_t3_cost = 0.0
    total_t2_income = 0.0
    total_t3_income = 0.0

    resolved_goals: list[tuple[Any, dict[str, Any]]] = []
    for goal in goal_structure_set.goals:
        candidates = matching_facilities(model, goal)
        if not candidates:
            continue
        # Use the most optimistic matching facility for capacity analysis.
        best = min(
            candidates,
            key=lambda item: sum(point_cost(item, goal.primary)),
        )
        resolved_goals.append((goal, best))
        location = facility_location(best["name"])
        used_by_location[location] += goal.count

    station_ranks: dict[str, list[int]] = {}
    station_rank = 0
    for goal, best in resolved_goals:
        if goal.primary or not is_station_structure(best["name"], model):
            continue
        ranks: list[int] = []
        for _ in range(goal.count):
            station_rank += 1
            ranks.append(station_rank)
        station_ranks[goal.goal_id] = ranks

    for goal, best in resolved_goals:
        ranks = station_ranks.get(goal.goal_id, [0] * goal.count)
        for copy_index in range(goal.count):
            rank = ranks[copy_index] if copy_index < len(ranks) else 0
            t2_effect, t3_effect = point_effects(
                best,
                primary=goal.primary,
                station_rank=rank,
                model=model,
            )
            total_t2_effect += t2_effect
            total_t3_effect += t3_effect
            total_t2_cost += max(0.0, -t2_effect)
            total_t3_cost += max(0.0, -t3_effect)
            total_t2_income += max(0.0, t2_effect)
            total_t3_income += max(0.0, t3_effect)

    point_budget: dict[str, Any] = {
        "orbital_used": used_by_location["orbital"],
        "surface_used": used_by_location["surface"],
        "orbital_available": survey_slot_capacity(survey, "orbital"),
        "surface_available": survey_slot_capacity(survey, "surface"),
        "t2_effect": total_t2_effect,
        "t3_effect": total_t3_effect,
        "t2_cost": total_t2_cost,
        "t3_cost": total_t3_cost,
        "t2_income": total_t2_income,
        "t3_income": total_t3_income,
    }

    for location in ("orbital", "surface"):
        available = survey_slot_capacity(survey, location)
        used = used_by_location[location]
        if available is None:
            point_budget[f"{location}_remaining"] = None
            if used > 0:
                needs_more_input = True
            continue
        point_budget[f"{location}_remaining"] = max(0, available - used)
        if available < used:
            unmet.append(
                f"{location} slot usage {used} exceeds available {available}"
            )

    remaining_orbital = point_budget.get("orbital_remaining")
    remaining_surface = point_budget.get("surface_remaining")
    if remaining_orbital is None or remaining_surface is None:
        if total_t2_effect < 0 or total_t3_effect < 0:
            needs_more_input = True
    else:
        max_t2_orbital, max_t3_orbital = _max_point_generation(model, "orbital")
        max_t2_surface, max_t3_surface = _max_point_generation(model, "surface")
        max_t2 = (
            remaining_orbital * max_t2_orbital
            + remaining_surface * max_t2_surface
        )
        max_t3 = (
            remaining_orbital * max_t3_orbital
            + remaining_surface * max_t3_surface
        )
        required_t2 = max(0.0, -total_t2_effect)
        required_t3 = max(0.0, -total_t3_effect)
        point_budget.update(
            {
                "required_t2": required_t2,
                "required_t3": required_t3,
                "max_t2_from_remaining": max_t2,
                "max_t3_from_remaining": max_t3,
            }
        )
        if required_t2 > max_t2:
            unmet.append("insufficient T2 point capacity for GoalStructureSet")
        if required_t3 > max_t3:
            unmet.append("insufficient T3 point capacity for GoalStructureSet")

    status = "feasible"
    if any_infeasible or unmet:
        status = "infeasible"
    elif needs_more_input:
        status = "needs_more_input"

    explanation = (
        "GoalStructureSet is feasible at the capacity level."
        if status == "feasible"
        else "GoalStructureSet needs attention before planning."
    )
    return FeasibilityResult(
        status=status,
        goal_results=goal_results,
        unmet_constraints=unmet,
        point_budget=point_budget,
        explanation=explanation,
    )
