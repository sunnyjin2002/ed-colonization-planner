"""Turn a feasible GoalStructureSet into a concrete colonization plan."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from domain import (
    facility_location,
    layout_options,
    matching_facilities,
    point_cost,
    survey_body,
)
from goal_set import Goal, GoalStructureSet
from state_store import SystemSurvey


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ConstructionItem:
    body_key: str
    facility: str
    layout_variant: str
    slot: str
    primary: bool
    build_order: int
    source_goal_id: str
    auto_prerequisite: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionItem":
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value.get(key) for key in allowed})


@dataclass
class Plan:
    plan_id: str
    system_name: str
    version: int
    status: str
    constructions: list[ConstructionItem]
    strategy_notes: str = ""
    validation_result: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "system_name": self.system_name,
            "version": self.version,
            "status": self.status,
            "constructions": [
                item.to_dict() for item in self.constructions
            ],
            "strategy_notes": self.strategy_notes,
            "validation_result": self.validation_result,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Plan":
        return cls(
            plan_id=value["plan_id"],
            system_name=value["system_name"],
            version=value.get("version", 1),
            status=value.get("status", "draft"),
            constructions=[
                ConstructionItem.from_dict(item)
                for item in value.get("constructions", [])
            ],
            strategy_notes=value.get("strategy_notes", ""),
            validation_result=value.get("validation_result", {}),
            created_at=value.get("created_at"),
            updated_at=value.get("updated_at"),
        )


def resolve_facility(
    goal: Goal,
    model: dict[str, Any],
) -> dict[str, Any]:
    candidates = matching_facilities(model, goal)
    if not candidates:
        raise ValueError(f"No facility matches goal {goal.goal_id}")
    # Prefer the least expensive matching facility for an initial concrete plan.
    return min(candidates, key=lambda item: sum(point_cost(item, goal.primary)))


def resolve_layout(
    structure_name: str,
    requested_variant: str | None,
    model: dict[str, Any],
) -> str | None:
    options = layout_options(model, structure_name)
    if not options:
        return None
    if requested_variant:
        return next(
            (
                item["layout_variant"]
                for item in options
                if item["layout_variant"] == requested_variant
            ),
            None,
        )

    def score(item: dict[str, Any]) -> tuple[int, int]:
        raw_score = item.get("score")
        return (raw_score if isinstance(raw_score, (int, float)) else 0, 0)

    return max(options, key=score).get("layout_variant")


def generate_plan(
    goal_structure_set: GoalStructureSet,
    survey: SystemSurvey,
    model: dict[str, Any],
    *,
    plan_id: str,
    version: int = 1,
) -> Plan:
    items: list[ConstructionItem] = []

    for goal_index, goal in enumerate(goal_structure_set.goals):
        body = survey_body(survey, goal.body_key)
        if body is None:
            raise ValueError(
                f"Goal {goal.goal_id} references unknown body {goal.body_key}"
            )

        structure = resolve_facility(goal, model)
        layout = resolve_layout(structure["name"], goal.layout_variant, model)
        for copy_index in range(goal.count):
            items.append(
                ConstructionItem(
                    body_key=goal.body_key,
                    facility=structure["name"],
                    layout_variant=layout,
                    slot=facility_location(structure["name"]),
                    primary=goal.primary,
                    build_order=0,
                    source_goal_id=goal.goal_id,
                )
            )

    primary_items = [item for item in items if item.primary]
    non_primary_items = [item for item in items if not item.primary]
    ordered = primary_items + non_primary_items
    for index, item in enumerate(ordered, start=1):
        item.build_order = index

    return Plan(
        plan_id=plan_id,
        system_name=survey.system_name,
        version=version,
        status="draft",
        constructions=ordered,
        strategy_notes=goal_structure_set.rationale,
    )
