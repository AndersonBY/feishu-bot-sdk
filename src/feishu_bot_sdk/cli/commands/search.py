from __future__ import annotations

import argparse
from typing import Any, Mapping

from ...search import SearchService
from ..runtime import _build_client, _parse_json_object


def _build_search_client(args: argparse.Namespace) -> SearchService:
    auth_mode = str(getattr(args, "auth_mode", "user") or "user").strip().lower()
    # Search APIs are user-token-first. Keep tenant mode only when explicitly requested.
    force_user_auth = auth_mode != "tenant"
    return SearchService(_build_client(args, force_user_auth=force_user_auth))


def _normalize_page_size(value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return 20


def _next_page_token(data: Mapping[str, Any]) -> str | None:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _cmd_search_app(args: argparse.Namespace) -> Mapping[str, Any]:
    service = _build_search_client(args)
    query = str(args.query)
    user_id_type = getattr(args, "user_id_type", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    if not bool(getattr(args, "all", False)):
        return service.search_apps(
            query,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
        )

    collected: list[Any] = []
    current_token = page_token
    while True:
        data = service.search_apps(
            query,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=current_token,
        )
        items = data.get("items")
        if isinstance(items, list):
            collected.extend(items)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
        page_size = _normalize_page_size(page_size)
    return {"all": True, "has_more": False, "count": len(collected), "items": collected}


def _cmd_search_message(args: argparse.Namespace) -> Mapping[str, Any]:
    service = _build_search_client(args)
    query = str(args.query)
    user_id_type = getattr(args, "user_id_type", None)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    from_ids = list(getattr(args, "from_ids", []) or [])
    chat_ids = list(getattr(args, "chat_ids", []) or [])
    message_type = getattr(args, "message_type", None)
    at_chatter_ids = list(getattr(args, "at_chatter_ids", []) or [])
    from_type = getattr(args, "from_type", None)
    chat_type = getattr(args, "chat_type", None)
    start_time = getattr(args, "start_time", None)
    end_time = getattr(args, "end_time", None)
    if not bool(getattr(args, "all", False)):
        return service.search_messages(
            query,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=page_token,
            from_ids=from_ids,
            chat_ids=chat_ids,
            message_type=message_type,
            at_chatter_ids=at_chatter_ids,
            from_type=from_type,
            chat_type=chat_type,
            start_time=start_time,
            end_time=end_time,
        )

    collected: list[Any] = []
    current_token = page_token
    while True:
        data = service.search_messages(
            query,
            user_id_type=user_id_type,
            page_size=page_size,
            page_token=current_token,
            from_ids=from_ids,
            chat_ids=chat_ids,
            message_type=message_type,
            at_chatter_ids=at_chatter_ids,
            from_type=from_type,
            chat_type=chat_type,
            start_time=start_time,
            end_time=end_time,
        )
        items = data.get("items")
        if isinstance(items, list):
            collected.extend(items)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
        page_size = _normalize_page_size(page_size)
    return {"all": True, "has_more": False, "count": len(collected), "items": collected}


def _cmd_search_doc_wiki(args: argparse.Namespace) -> Mapping[str, Any]:
    if bool(getattr(args, "doc_filter_stdin", False)) and bool(getattr(args, "wiki_filter_stdin", False)):
        raise ValueError("--doc-filter-stdin and --wiki-filter-stdin cannot be used together")

    doc_filter = _parse_json_object(
        json_text=getattr(args, "doc_filter_json", None),
        file_path=getattr(args, "doc_filter_file", None),
        stdin_enabled=bool(getattr(args, "doc_filter_stdin", False)),
        name="doc-filter",
        required=False,
    )
    wiki_filter = _parse_json_object(
        json_text=getattr(args, "wiki_filter_json", None),
        file_path=getattr(args, "wiki_filter_file", None),
        stdin_enabled=bool(getattr(args, "wiki_filter_stdin", False)),
        name="wiki-filter",
        required=False,
    )
    if not doc_filter and not wiki_filter:
        raise ValueError(
            "search doc-wiki requires at least one of doc_filter or wiki_filter "
            "(use --doc-filter-json/--wiki-filter-json or corresponding file/stdin flags)"
        )

    service = _build_search_client(args)
    query = str(args.query)
    page_size = getattr(args, "page_size", None)
    page_token = getattr(args, "page_token", None)
    normalized_doc_filter = doc_filter or None
    normalized_wiki_filter = wiki_filter or None
    if not bool(getattr(args, "all", False)):
        return service.search_doc_wiki(
            query,
            doc_filter=normalized_doc_filter,
            wiki_filter=normalized_wiki_filter,
            page_size=page_size,
            page_token=page_token,
        )

    collected: list[Any] = []
    current_token = page_token
    while True:
        data = service.search_doc_wiki(
            query,
            doc_filter=normalized_doc_filter,
            wiki_filter=normalized_wiki_filter,
            page_size=page_size,
            page_token=current_token,
        )
        items = data.get("res_units")
        if isinstance(items, list):
            collected.extend(items)
        if not _has_more(data):
            break
        current_token = _next_page_token(data)
        if not current_token:
            break
        page_size = _normalize_page_size(page_size)
    return {"all": True, "has_more": False, "count": len(collected), "res_units": collected}


__all__ = [name for name in globals() if name.startswith("_cmd_")]
