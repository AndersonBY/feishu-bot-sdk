from __future__ import annotations

from typing import Any, Iterator, Mapping, Sequence

from ..response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _normalize_mapping(payload: Mapping[str, object]) -> dict[str, object]:
    return {str(key): value for key, value in payload.items()}


def _normalize_mappings(values: Sequence[Mapping[str, object]], *, name: str) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for value in values:
        normalized.append(_normalize_mapping(value))
    if not normalized:
        raise ValueError(f"{name} must contain at least one item")
    return normalized


def _normalize_ids(values: Sequence[str], *, name: str) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        normalized.append(text)
    if not normalized:
        raise ValueError(f"{name} must contain at least one non-empty value")
    return normalized


def _iter_page_items(data: Mapping[str, Any], *, key: str = "items") -> Iterator[Any]:
    items = data.get(key)
    if not isinstance(items, list):
        return
    for item in items:
        yield item


def _next_page_token(data: Mapping[str, Any]) -> str | None:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


__all__ = [
    "_drop_none",
    "_unwrap_data",
    "_normalize_mapping",
    "_normalize_mappings",
    "_normalize_ids",
    "_iter_page_items",
    "_next_page_token",
    "_has_more",
]
