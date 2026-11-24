"""Structured player goals used by feasibility, strategy, and planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


GOAL_PRIORITIES = {"must", "prefer", "optional"}


@dataclass
class Goal:
    """A user intent that should be represented in a colony plan.

    A goal is intentionally not a complete construction row. It may specify an
    exact facility, or only a facility class and tier. Plan generation resolves
    partial goals into concrete facilities and layout variants.
    """

    goal_id: str
    body_key: str
    facility: str | None = None
    facility_class: str | None = None
    tier: int | None = None
    primary: bool = False
    layout_variant: str | None = None
    priority: str = "must"
    source: str = "player"
    note: str = ""
    count: int = 1

    def __post_init__(self) -> None:
        if self.priority not in GOAL_PRIORITIES:
            raise ValueError(f"Invalid goal priority: {self.priority}")
        if self.count < 1:
            raise ValueError("Goal count must be at least 1")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Goal":
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value.get(key) for key in allowed})


@dataclass
class StrategyIntent:
    """A high-level objective that still needs to become concrete structures.

    Example:

        StrategyIntent(
            intent_id="intent-refinery",
            objective="robust_refinery_economy",
            intensity="robust",
            constraints=["avoid_military"],
        )
    """

    intent_id: str
    objective: str
    intensity: str = "balanced"
    body_preferences: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    note: str = ""
    source: str = "player"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "StrategyIntent":
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value.get(key) for key in allowed})


@dataclass
class GoalStructureSet:
    """A collection of concrete construction goals for planning tools."""

    goals: list[Goal] = field(default_factory=list)
    strategy_id: str | None = None
    rationale: str = ""

    def add(self, goal: Goal) -> None:
        self.goals.append(goal)

    def primary_goals(self) -> list[Goal]:
        return [goal for goal in self.goals if goal.primary]

    def to_dict(self) -> dict[str, Any]:
        return {
            "goals": [goal.to_dict() for goal in self.goals],
            "strategy_id": self.strategy_id,
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "GoalStructureSet":
        return cls(
            goals=[Goal.from_dict(item) for item in value.get("goals", [])],
            strategy_id=value.get("strategy_id"),
            rationale=value.get("rationale", ""),
        )
