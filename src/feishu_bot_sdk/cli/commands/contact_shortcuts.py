from __future__ import annotations

import argparse
import re
from html import unescape
from typing import Any, Mapping
from urllib.parse import quote

from ..runtime import _build_client


_DISPLAY_INFO_HIGHLIGHT_RE = re.compile(r"<h>(.*?)</h>")
_DISPLAY_INFO_RECENCY_RE = re.compile(r"^\[(.+)\]$")
_SEARCH_BOOL_FILTERS: dict[str, str] = {
    "left_organization": "is_resigned",
    "has_chatted": "has_contact",
    "exclude_external_users": "exclude_outer_contact",
    "has_enterprise_email": "has_enterprise_email",
}
_FIXED_LOCALE_FALLBACK = (
    "ja_jp",
    "zh_hk",
    "zh_tw",
    "ko_kr",
    "id_id",
    "vi_vn",
    "th_th",
    "pt_br",
    "es_es",
    "de_de",
    "fr_fr",
    "it_it",
    "ru_ru",
)


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _list_items(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _is_bot_identity(args: argparse.Namespace) -> bool:
    return str(getattr(args, "auth_mode", "") or "").strip().lower() == "tenant"


def _pick_name(i18n: Mapping[str, Any], lang: str | None, open_id: str) -> str:
    candidates: list[str] = []
    if lang:
        candidates.append(str(lang).strip().lower().replace("-", "_"))
    candidates.extend(["zh_cn", "en_us"])
    candidates.extend(_FIXED_LOCALE_FALLBACK)
    for key in candidates:
        value = i18n.get(key)
        if isinstance(value, str) and value:
            return value
    for key in sorted(str(item) for item in i18n):
        value = i18n.get(key)
        if isinstance(value, str) and value:
            return value
    return open_id


def _parse_display_info(raw: Any) -> tuple[list[str], str, str]:
    text = str(raw or "")
    segments = [unescape(item) for item in _DISPLAY_INFO_HIGHLIGHT_RE.findall(text)]
    lines = text.splitlines()
    department = lines[1].strip() if len(lines) >= 2 else ""
    recency = ""
    for line in reversed(lines):
        match = _DISPLAY_INFO_RECENCY_RE.match(line.strip())
        if match:
            recency = match.group(1)
            break
    return segments, department, recency


def _project_search_user(item: Mapping[str, Any], *, lang: str | None) -> dict[str, Any]:
    meta = item.get("meta_data")
    meta_map = meta if isinstance(meta, Mapping) else {}
    i18n_names = meta_map.get("i18n_names")
    i18n_map = i18n_names if isinstance(i18n_names, Mapping) else {}
    open_id = str(item.get("id") or "")
    segments, department, recency = _parse_display_info(item.get("display_info"))
    chat_id = str(meta_map.get("chat_id") or "")
    return {
        "open_id": open_id,
        "localized_name": _pick_name(i18n_map, lang, open_id),
        "email": str(meta_map.get("mail_address") or ""),
        "enterprise_email": str(meta_map.get("enterprise_mail_address") or ""),
        "is_activated": bool(meta_map.get("is_registered")),
        "is_cross_tenant": bool(meta_map.get("is_cross_tenant")),
        "p2p_chat_id": chat_id,
        "has_chatted": bool(chat_id),
        "department": department,
        "signature": str(meta_map.get("description") or ""),
        "chat_recency_hint": recency,
        "match_segments": segments,
    }


def _build_search_user_filter(args: argparse.Namespace, *, allow_user_ids: bool = True) -> dict[str, Any]:
    filter_payload: dict[str, Any] = {}
    if allow_user_ids:
        user_ids = _split_csv(getattr(args, "user_ids", None))
        if user_ids:
            if len(user_ids) > 100:
                raise ValueError("--user-ids: must be at most 100 entries")
            filter_payload["user_ids"] = user_ids
    for arg_name, api_name in _SEARCH_BOOL_FILTERS.items():
        if bool(getattr(args, arg_name, False)):
            filter_payload[api_name] = True
    return filter_payload


def _build_search_user_body(args: argparse.Namespace, *, query: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {}
    query_value = str(query if query is not None else getattr(args, "query", "") or "").strip()
    if query_value:
        if len(query_value) > 50:
            raise ValueError("--query: length must be between 1 and 50 characters")
        body["query"] = query_value
    filter_payload = _build_search_user_filter(args, allow_user_ids=query is None)
    if filter_payload:
        body["filter"] = filter_payload
    return body


def _validate_search_user_args(args: argparse.Namespace) -> None:
    has_query = bool(str(getattr(args, "query", "") or "").strip())
    queries = _split_csv(getattr(args, "queries", None))
    has_user_ids = bool(_split_csv(getattr(args, "user_ids", None)))
    has_bool_filter = any(bool(getattr(args, name, False)) for name in _SEARCH_BOOL_FILTERS)
    if not any((has_query, queries, has_user_ids, has_bool_filter)):
        raise ValueError(
            "specify at least one of --query, --queries, --user-ids, --has-chatted, "
            "--has-enterprise-email, --exclude-external-users, --left-organization"
        )
    if queries:
        if has_query:
            raise ValueError("--query and --queries are mutually exclusive")
        if has_user_ids:
            raise ValueError("--user-ids and --queries are mutually exclusive")
        if len(queries) > 20:
            raise ValueError(f"--queries: must be at most 20 entries (got {len(queries)})")
        for item in queries:
            if len(item) > 50:
                raise ValueError(f"--queries: entry {item!r} exceeds 50 characters")
    page_size = int(getattr(args, "page_size", 20) or 20)
    if page_size < 1 or page_size > 30:
        raise ValueError("--page-size: must be between 1 and 30")


def _cmd_contact_get_user(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    user_id = str(getattr(args, "user_id", "") or "").strip()
    user_id_type = str(getattr(args, "user_id_type", "") or "").strip() or "open_id"

    if not user_id:
        if _is_bot_identity(args):
            raise ValueError("bot identity cannot get current user info, specify --user-id")
        data = _data(client.request_json("GET", "/authen/v1/user_info"))
        return {"user": data}

    if _is_bot_identity(args):
        data = _data(
            client.request_json(
                "GET",
                f"/contact/v3/users/{quote(user_id, safe='')}",
                params={"user_id_type": user_id_type},
            )
        )
        user = data.get("user")
        return {"user": dict(user) if isinstance(user, Mapping) else data}

    data = _data(
        client.request_json(
            "POST",
            "/contact/v3/users/basic_batch",
            params={"user_id_type": user_id_type},
            payload={"user_ids": [user_id]},
        )
    )
    users = data.get("users")
    user = users[0] if isinstance(users, list) and users and isinstance(users[0], Mapping) else {}
    return {"user": dict(user)}


def _cmd_contact_search_user(args: argparse.Namespace) -> Mapping[str, Any]:
    _validate_search_user_args(args)
    client = _build_client(args)
    page_size = int(getattr(args, "page_size", 20) or 20)
    lang = str(getattr(args, "lang", "") or "").strip() or None
    queries = _split_csv(getattr(args, "queries", None))

    if queries:
        flattened: list[dict[str, Any]] = []
        summaries: list[dict[str, Any]] = []
        for query in queries:
            data = _data(
                client.request_json(
                    "POST",
                    "/contact/v3/users/search",
                    params={"page_size": page_size},
                    payload=_build_search_user_body(args, query=query),
                )
            )
            items = _list_items(data.get("items"))
            for item in items:
                if isinstance(item, Mapping):
                    user = _project_search_user(item, lang=lang)
                    user["matched_query"] = query
                    flattened.append(user)
            summaries.append({"query": query, "has_more": bool(data.get("has_more"))})
        return {"users": flattened, "queries": summaries}

    data = _data(
        client.request_json(
            "POST",
            "/contact/v3/users/search",
            params={"page_size": page_size},
            payload=_build_search_user_body(args),
        )
    )
    items = _list_items(data.get("items"))
    users = [_project_search_user(item, lang=lang) for item in items if isinstance(item, Mapping)]
    return {
        "users": users,
        "has_more": bool(data.get("has_more")),
        "page_token": data.get("page_token"),
    }


__all__ = ["_cmd_contact_get_user", "_cmd_contact_search_user"]
