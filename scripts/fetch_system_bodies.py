"""Fetch normalized system body data from EDSM.

The primary use is to build an editable SystemSurvey for the colonisation
planner. Exact construction site counts and primary-port placement are always
left for the player to supply.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from state_store import BodySurvey, SystemSurvey


EDSM_SYSTEM_URL = "https://www.edsm.net/api-v1/system"
EDSM_BODIES_URL = "https://www.edsm.net/api-system-v1/bodies"
DEFAULT_USER_AGENT = "ed-colonization-planner/0.1"


class DataSourceError(RuntimeError):
    """Raised when an external data source cannot provide a usable response."""


def _request_json(
    url: str,
    params: dict[str, str],
    *,
    timeout: int = 30,
) -> dict[str, Any]:
    query = urlencode(params)
    request = Request(
        f"{url}?{query}",
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as exc:
        raise DataSourceError(f"EDSM returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise DataSourceError(f"EDSM request failed: {exc.reason}") from exc

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataSourceError("EDSM returned non-JSON data") from exc
    if not isinstance(payload, dict):
        raise DataSourceError("EDSM returned an unexpected response shape")
    return payload


def fetch_system_info(system_name: str) -> dict[str, Any]:
    """Fetch population and government information for a system."""
    return _request_json(
        EDSM_SYSTEM_URL,
        {
            "systemName": system_name,
            "showInformation": "1",
            "showPrimaryStar": "1",
            "showCoordinates": "1",
        },
    )


def fetch_bodies(system_name: str) -> dict[str, Any]:
    """Fetch the body list for a system."""
    return _request_json(
        EDSM_BODIES_URL,
        {"systemName": system_name},
    )


def _parent_type_and_id(parents: Any) -> tuple[str | None, int | None]:
    if not isinstance(parents, list):
        return None, None

    for parent in parents:
        if not isinstance(parent, dict):
            continue
        for parent_type in ("Planet", "Star", "Null"):
            if parent_type in parent:
                value = parent[parent_type]
                try:
                    return parent_type, int(value)
                except (TypeError, ValueError):
                    return parent_type, None
    return None, None


def _letter_suffix(index: int) -> str:
    """Return Excel-like lowercase letters: a, b, ..., z, aa, ab."""
    result = ""
    index += 1
    while index:
        index, remainder = divmod(index - 1, 26)
        result = chr(ord("a") + remainder) + result
    return result


def derive_body_keys(bodies: list[dict[str, Any]]) -> dict[int, str]:
    """Assign human-readable system-map keys such as A1 or A3a.

    EDSM does not return Frontier's system-map labels directly. This is a
    best-effort mapping based on parent relationships and distance from the
    arrival star. It is good enough for display and conversation references,
    but the player's in-game body name remains authoritative.
    """
    by_id: dict[int, dict[str, Any]] = {}
    for body in bodies:
        body_id = body.get("bodyId")
        if isinstance(body_id, int):
            by_id[body_id] = body

    keys: dict[int, str] = {}
    star_letter_index = 0
    for body in bodies:
        body_id = body.get("bodyId")
        if not isinstance(body_id, int):
            continue
        if body.get("type") == "Star":
            keys[body_id] = chr(ord("A") + star_letter_index)
            star_letter_index += 1

    children_by_parent: dict[tuple[str, int], list[dict[str, Any]]] = {}
    fallback_children: list[dict[str, Any]] = []
    for body in bodies:
        body_id = body.get("bodyId")
        if not isinstance(body_id, int):
            continue
        if body.get("type") == "Star":
            continue
        parent_type, parent_id = _parent_type_and_id(body.get("parents"))
        if parent_type in {"Planet", "Star"} and parent_id in by_id:
            children_by_parent.setdefault((parent_type, parent_id), []).append(body)
        elif parent_type == "Star":
            fallback_children.append(body)
        else:
            fallback_children.append(body)

    def sort_key(item: dict[str, Any]) -> tuple[float, float]:
        distance = item.get("distanceToArrival")
        axis = item.get("semiMajorAxis")
        return (
            float(distance) if isinstance(distance, (int, float)) else float("inf"),
            float(axis) if isinstance(axis, (int, float)) else float("inf"),
        )

    for (parent_type, parent_id), children in children_by_parent.items():
        children.sort(key=sort_key)
        for index, child in enumerate(children):
            child_id = child.get("bodyId")
            if not isinstance(child_id, int):
                continue
            if parent_type == "Star":
                keys[child_id] = f"{keys.get(parent_id, 'A')}{index + 1}"
            else:
                keys[child_id] = f"{keys.get(parent_id, 'U')}{_letter_suffix(index)}"

    for child in fallback_children:
        child_id = child.get("bodyId")
        if isinstance(child_id, int) and child_id not in keys:
            keys[child_id] = f"U{child_id}"

    return keys


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_body(
    raw_body: dict[str, Any],
    body_key: str | None,
) -> BodySurvey:
    """Map an EDSM body record to the planner's survey body model."""
    body_id = raw_body.get("bodyId")
    parents = raw_body.get("parents")
    parent_type, parent_id = _parent_type_and_id(parents)
    return BodySurvey(
        body_key=body_key or (str(body_id) if body_id is not None else raw_body.get("name")),
        name=raw_body.get("name"),
        body_type=raw_body.get("type"),
        sub_type=raw_body.get("subType"),
        is_landable=raw_body.get("isLandable"),
        distance_to_arrival=_as_float(raw_body.get("distanceToArrival")),
        gravity=_as_float(raw_body.get("gravity")),
        surface_temperature=_as_float(raw_body.get("surfaceTemperature")),
        atmosphere=raw_body.get("atmosphereType"),
        volcanism=raw_body.get("volcanismType"),
        terraforming_state=raw_body.get("terraformingState"),
        source="edsm",
        notes=f"parent_type={parent_type}; parent_id={parent_id}",
    )


def build_survey(
    system_name: str,
    *,
    system_info: dict[str, Any] | None = None,
    bodies_payload: dict[str, Any] | None = None,
) -> SystemSurvey:
    """Create an editable SystemSurvey from EDSM payloads."""
    raw_bodies = (bodies_payload or {}).get("bodies", [])
    keys = derive_body_keys(raw_bodies) if raw_bodies else {}
    survey = SystemSurvey(
        system_name=system_name,
        provider="edsm",
        raw_system_data={
            "system": system_info or {},
            "body_count": (bodies_payload or {}).get("bodyCount"),
        },
    )
    survey.bodies = [
        normalize_body(body, keys.get(body.get("bodyId")))
        for body in raw_bodies
    ]

    information = (system_info or {}).get("information") or {}
    survey.missing_fields = [
        "orbital_construction_sites",
        "surface_construction_sites",
        "primary_port_body",
    ]
    if not information.get("population"):
        survey.raw_system_data["population_known"] = False
    else:
        survey.raw_system_data["population_known"] = True

    return survey


def survey_system(system_name: str) -> SystemSurvey:
    """Fetch and normalize EDSM data for one system."""
    system_info = fetch_system_info(system_name)
    bodies_payload = fetch_bodies(system_name)
    return build_survey(
        system_name,
        system_info=system_info,
        bodies_payload=bodies_payload,
    )


def empty_survey(system_name: str) -> SystemSurvey:
    """Return a manual-entry survey when no external data is available."""
    survey = SystemSurvey(system_name=system_name, provider="manual")
    survey.missing_fields = [
        "bodies",
        "orbital_construction_sites",
        "surface_construction_sites",
        "primary_port_body",
    ]
    return survey


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", required=True, help="System name to survey.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path where the survey JSON should be written.",
    )
    parser.add_argument(
        "--empty",
        action="store_true",
        help="Skip EDSM and emit an empty manual survey.",
    )
    args = parser.parse_args()

    if args.empty:
        survey = empty_survey(args.system)
    else:
        try:
            survey = survey_system(args.system)
        except DataSourceError as exc:
            print(f"EDSM error: {exc}", file=sys.stderr)
            survey = empty_survey(args.system)
            survey.raw_system_data["data_source_error"] = str(exc)

    payload = survey.to_dict()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Bodies: {len(survey.bodies)}")
    print(f"Missing: {survey.missing_fields}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
