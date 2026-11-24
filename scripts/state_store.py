"""Conversation-scoped state models and storage adapters.

The colonisation planner is a stateless workflow. User-specific survey and
plan data is owned by the host conversation, not by the skill directory.
These adapters keep that boundary explicit.
"""

from __future__ import annotations

import json
import re
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BodySurvey:
    """Normalized body record from an external source or manual entry."""

    body_key: str
    name: str
    body_type: str | None = None
    sub_type: str | None = None
    is_landable: bool | None = None
    distance_to_arrival: float | None = None
    gravity: float | None = None
    surface_temperature: float | None = None
    atmosphere: str | None = None
    volcanism: str | None = None
    terraforming_state: str | None = None
    orbital_site_candidates: int | None = None
    surface_site_candidates: int | None = None
    manual_orbital_sites: int | None = None
    manual_surface_sites: int | None = None
    primary_port: bool = False
    notes: str = ""
    source: str = "external"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "BodySurvey":
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value.get(key) for key in allowed})


@dataclass
class SystemSurvey:
    """Editable system survey state for one conversation."""

    system_name: str
    provider: str | None = None
    fetched_at: str | None = None
    bodies: list[BodySurvey] = field(default_factory=list)
    manual_overrides: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    primary_port_candidates: list[str] = field(default_factory=list)
    raw_system_data: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "system_name": self.system_name,
            "provider": self.provider,
            "fetched_at": self.fetched_at,
            "bodies": [body.to_dict() for body in self.bodies],
            "manual_overrides": self.manual_overrides,
            "missing_fields": self.missing_fields,
            "primary_port_candidates": self.primary_port_candidates,
            "raw_system_data": self.raw_system_data,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SystemSurvey":
        bodies = [BodySurvey.from_dict(item) for item in value.get("bodies", [])]
        return cls(
            system_name=value["system_name"],
            provider=value.get("provider"),
            fetched_at=value.get("fetched_at"),
            bodies=bodies,
            manual_overrides=value.get("manual_overrides", {}),
            missing_fields=value.get("missing_fields", []),
            primary_port_candidates=value.get("primary_port_candidates", []),
            raw_system_data=value.get("raw_system_data", {}),
            updated_at=value.get("updated_at"),
        )


@dataclass
class ColonizationPlan:
    """Versioned plan state for one conversation."""

    plan_id: str
    system_name: str
    version: int = 1
    status: str = "draft"
    selected_constructions: list[dict[str, Any]] = field(default_factory=list)
    strategy_notes: str = ""
    validation_result: dict[str, Any] = field(default_factory=dict)
    export_status: str | None = None
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ColonizationPlan":
        allowed = {item.name for item in cls.__dataclass_fields__.values()}
        return cls(**{key: value.get(key) for key in allowed})


class StateStore(ABC):
    """Small storage contract used by the skill."""

    @abstractmethod
    def get(self, scope: str, key: str) -> dict[str, Any] | None:
        raise NotImplementedError

    @abstractmethod
    def put(self, scope: str, key: str, value: dict[str, Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete(self, scope: str, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def list_keys(self, scope: str) -> list[str]:
        raise NotImplementedError


class MemoryStateStore(StateStore):
    """In-memory store for tests and short-lived single-process sessions."""

    def __init__(self) -> None:
        self._data: dict[str, dict[str, dict[str, Any]]] = {}

    def get(self, scope: str, key: str) -> dict[str, Any] | None:
        return self._data.get(scope, {}).get(key)

    def put(self, scope: str, key: str, value: dict[str, Any]) -> None:
        self._data.setdefault(scope, {})[key] = value

    def delete(self, scope: str, key: str) -> None:
        self._data.get(scope, {}).pop(key, None)

    def list_keys(self, scope: str) -> list[str]:
        return sorted(self._data.get(scope, {}).keys())


class JsonFileStateStore(StateStore):
    """Base class for file-backed stores.

    The scope is converted into a safe directory component so conversation
    identifiers cannot escape the configured root.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def _scope_dir(self, scope: str) -> Path:
        safe_scope = re.sub(r"[^A-Za-z0-9_.-]", "_", scope)
        return self.root / safe_scope

    def _key_path(self, scope: str, key: str) -> Path:
        safe_key = re.sub(r"[^A-Za-z0-9_.-]", "_", key)
        return self._scope_dir(scope) / f"{safe_key}.json"

    def get(self, scope: str, key: str) -> dict[str, Any] | None:
        path = self._key_path(scope, key)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, scope: str, key: str, value: dict[str, Any]) -> None:
        path = self._key_path(scope, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def delete(self, scope: str, key: str) -> None:
        path = self._key_path(scope, key)
        if path.exists():
            path.unlink()

    def list_keys(self, scope: str) -> list[str]:
        scope_dir = self._scope_dir(scope)
        if not scope_dir.exists():
            return []
        return sorted(path.stem for path in scope_dir.glob("*.json"))


class TempFileStateStore(JsonFileStateStore):
    """File store under the OS temp directory."""

    def __init__(self, root: Path | None = None) -> None:
        super().__init__(
            root or Path(tempfile.gettempdir()) / "ed-colonization-planner-state"
        )


class WorkspaceStateStore(JsonFileStateStore):
    """File store under an explicitly provided workspace directory."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)


def survey_store_key(system_name: str) -> str:
    """Return the conventional key for a system survey."""
    return f"survey::{system_name.lower()}"


def plan_store_key(plan_id: str) -> str:
    """Return the conventional key for a plan version."""
    return f"plan::{plan_id}"
