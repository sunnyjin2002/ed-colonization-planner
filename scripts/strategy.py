"""Generate candidate colonisation strategies when the player has no fixed goal."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from domain import body_slot_capacity, structure_by_name
from goal_set import Goal, GoalStructureSet
from state_store import SystemSurvey


@dataclass
class StrategySuggestion:
    strategy_id: str
    title: str
    rationale: str
    goals: list[Goal]
    risks: list[str] = field(default_factory=list)
    body_scores: list[dict[str, Any]] = field(default_factory=list)

    def to_goal_structure_set(self) -> GoalStructureSet:
        return GoalStructureSet(
            goals=self.goals,
            strategy_id=self.strategy_id,
            rationale=self.rationale,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "title": self.title,
            "rationale": self.rationale,
            "goals": [goal.to_dict() for goal in self.goals],
            "risks": self.risks,
            "body_scores": self.body_scores,
        }


def _body_with_capacity(
    survey: SystemSurvey,
    location: str,
    minimum: int = 1,
) -> Any:
    candidates = [
        (body, body_slot_capacity(body, location) or 0)
        for body in survey.bodies
        if (body_slot_capacity(body, location) or 0) >= minimum
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[1])[0]


def _primary_facility(orbital_capacity: int | None) -> str:
    if orbital_capacity is not None and orbital_capacity <= 1:
        return "Orbital - Outpost - Commercial (Primary)"
    return "Orbital - Starport - Coriolis (Primary)"


def _goal(
    goal_id: str,
    body_key: str,
    facility: str,
    *,
    primary: bool = False,
) -> Goal:
    return Goal(
        goal_id=goal_id,
        body_key=body_key,
        facility=facility,
        primary=primary,
        priority="prefer",
        source="strategy",
    )


def _score_bodies(survey: SystemSurvey) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for body in survey.bodies:
        orbital = body_slot_capacity(body, "orbital") or 0
        surface = body_slot_capacity(body, "surface") or 0
        score = orbital * 3 + surface * 2
        if body.body_type == "Planet":
            if body.sub_type == "Earth-like world":
                score += 8
            if body.terraforming_state == "Terraformable":
                score += 5
            if body.is_landable:
                score += 2
        scores.append(
            {
                "body_key": body.body_key,
                "name": body.name,
                "orbital_capacity": orbital,
                "surface_capacity": surface,
                "score": score,
            }
        )
    return sorted(scores, key=lambda item: item["score"], reverse=True)


def suggest_strategies(
    survey: SystemSurvey,
    model: dict[str, Any],
) -> list[StrategySuggestion]:
    body_scores = _score_bodies(survey)
    if not body_scores:
        return []

    orbital_body = _body_with_capacity(survey, "orbital") or survey.bodies[0]
    surface_body = _body_with_capacity(survey, "surface") or survey.bodies[0]
    orbital_capacity = body_slot_capacity(orbital_body, "orbital")
    primary_facility = _primary_facility(orbital_capacity)

    strategies: list[StrategySuggestion] = []

    balanced = StrategySuggestion(
        strategy_id="balanced-colony",
        title="Balanced Colony",
        rationale=(
            "Use the primary orbital slot for a general-purpose station, "
            "then add trade and population support on the surface."
        ),
        goals=[
            _goal(
                "B1",
                orbital_body.body_key,
                primary_facility,
                primary=True,
            ),
            _goal(
                "B2",
                surface_body.body_key,
                "Surface - Settlement - Agriculture T1 M",
            ),
            _goal(
                "B3",
                orbital_body.body_key,
                "Orbital - Outpost - Commercial",
            ),
        ],
        risks=["Low specialization", "Limited score growth"],
        body_scores=body_scores,
    )
    strategies.append(balanced)

    if structure_by_name(model, "Surface - Settlement - Extraction T1 M"):
        extraction = StrategySuggestion(
            strategy_id="extraction-refinery",
            title="Extraction and Refinery",
            rationale=(
                "Concentrate surface construction around extraction and "
                "refinery economies to feed industrial expansion."
            ),
            goals=[
                _goal(
                    "E1",
                    orbital_body.body_key,
                    primary_facility,
                    primary=True,
                ),
                _goal(
                    "E2",
                    surface_body.body_key,
                    "Surface - Settlement - Extraction T1 M",
                ),
                _goal(
                    "E3",
                    surface_body.body_key,
                    "Surface - Hub - Refinery",
                ),
            ],
            risks=[
                "Refinery hub has prerequisites",
                "Needs enough surface slots",
            ],
            body_scores=body_scores,
        )
        strategies.append(extraction)

    if structure_by_name(model, "Surface - Settlement - Research Bio T1 M"):
        high_tech = StrategySuggestion(
            strategy_id="high-tech-research",
            title="High Tech and Research",
            rationale=(
                "Use research settlements and a high-tech hub to develop "
                "advanced services and technology."
            ),
            goals=[
                _goal(
                    "H1",
                    orbital_body.body_key,
                    primary_facility,
                    primary=True,
                ),
                _goal(
                    "H2",
                    surface_body.body_key,
                    "Surface - Settlement - Research Bio T1 M",
                ),
                _goal(
                    "H3",
                    surface_body.body_key,
                    "Surface - Hub - High Tech",
                ),
            ],
            risks=[
                "High Tech hub has prerequisites",
                "Requires sufficient surface construction sites",
            ],
            body_scores=body_scores,
        )
        strategies.append(high_tech)

    return strategies
