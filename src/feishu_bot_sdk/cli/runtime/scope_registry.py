from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from .registry import iter_methods, metadata_root


def _scope_file(name: str) -> Path:
    return metadata_root() / name


@lru_cache(maxsize=1)
def load_scope_priorities() -> dict[str, int]:
    payload = _load_json_list(_scope_file("scope_priorities.json"))
    priorities: dict[str, int] = {}
    for item in payload:
        scope_name = str(item.get("scope_name") or "").strip()
        if not scope_name:
            continue
        score_raw = item.get("final_score")
        if score_raw is None:
            continue
        try:
            priorities[scope_name] = int(round(float(score_raw)))
        except (TypeError, ValueError):
            continue
    overrides = _load_json(_scope_file("scope_overrides.json"))
    for scope_name, score in (overrides.get("priority_overrides") or {}).items():
        try:
            priorities[str(scope_name)] = int(score)
        except (TypeError, ValueError):
            continue
    return priorities


@lru_cache(maxsize=1)
def load_auto_approve_scopes() -> set[str]:
    approved: set[str] = set()
    for item in _load_json_list(_scope_file("scope_priorities.json")):
        if str(item.get("recommend") or "").lower() == "true":
            scope_name = str(item.get("scope_name") or "").strip()
            if scope_name:
                approved.add(scope_name)
    overrides = _load_json(_scope_file("scope_overrides.json"))
    recommend_overrides = overrides.get("recommend")
    if isinstance(recommend_overrides, dict):
        allow = recommend_overrides.get("allow", [])
        deny = recommend_overrides.get("deny", [])
    else:
        allow = overrides.get("auto_approve_allow", [])
        deny = overrides.get("auto_approve_deny", [])
    for scope_name in allow or []:
        approved.add(str(scope_name))
    for scope_name in deny or []:
        approved.discard(str(scope_name))
    return approved


def collect_all_scopes(identity: str, *, services: Iterable[str] | None = None) -> list[str]:
    scopes: set[str] = set()
    for method in iter_methods(services):
        if identity not in method.supported_identities:
            continue
        scopes.update(method.required_scopes or method.scopes)
    return sorted(scopes)


def recommend_scopes(identity: str, *, services: Iterable[str] | None = None) -> list[str]:
    priorities = load_scope_priorities()
    recommended: set[str] = set()
    for method in iter_methods(services):
        if identity not in method.supported_identities:
            continue
        method_scopes = method.required_scopes or method.scopes
        if not method_scopes:
            continue
        best_scope = max(method_scopes, key=lambda item: priorities.get(item, 0))
        recommended.add(best_scope)
    return sorted(recommended)


def missing_scopes(granted_scope_text: str | None, required: Iterable[str]) -> list[str]:
    granted = {item.strip() for item in str(granted_scope_text or "").split() if item.strip()}
    return sorted(scope for scope in required if scope not in granted)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _load_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


__all__ = [
    "collect_all_scopes",
    "load_auto_approve_scopes",
    "load_scope_priorities",
    "missing_scopes",
    "recommend_scopes",
]
