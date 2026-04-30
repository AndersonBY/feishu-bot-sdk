from __future__ import annotations

import argparse
import json
import re
from email.message import Message
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import quote

import httpx

from ...exceptions import HTTPRequestError
from ..runtime import _build_client


_MENTION_RE = re.compile(r"<at\s+(?:id|open_id|user_id)=(\"?)([^\"\s/>]+)\1\s*/?>")


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _normalize_at_mentions(text: str) -> str:
    return _MENTION_RE.sub(r'<at user_id="\2">', text)


def _json_content_from_text(text: str) -> str:
    return json.dumps({"text": _normalize_at_mentions(text)}, ensure_ascii=False)


def _message_content(args: argparse.Namespace) -> tuple[str, str]:
    text = str(getattr(args, "text", "") or "")
    if text:
        return "text", _json_content_from_text(text)
    content = str(getattr(args, "content", "") or "").strip()
    msg_type = str(getattr(args, "msg_type", "") or "text").strip() or "text"
    if content:
        if msg_type in {"text", "post"}:
            content = _normalize_at_mentions(content)
        return msg_type, content
    raise ValueError("specify one of --text or --content")


def _chat_create_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "chat_type": str(getattr(args, "type", "") or "private").strip() or "private",
    }
    fields = (
        ("name", "name"),
        ("description", "description"),
        ("owner", "owner_id"),
    )
    for attr, key in fields:
        value = str(getattr(args, attr, "") or "").strip()
        if value:
            body[key] = value
    users = _split_csv(getattr(args, "users", None))
    if users:
        body["user_id_list"] = users
    bots = _split_csv(getattr(args, "bots", None))
    if bots:
        body["bot_id_list"] = bots
    return body


def _cmd_im_chat_create(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    params: dict[str, Any] = {"user_id_type": "open_id"}
    if bool(getattr(args, "set_bot_manager", False)):
        params["set_bot_manager"] = True
    data = _data(client.request_json("POST", "/im/v1/chats", params=params, payload=_chat_create_body(args)))
    result = dict(data)
    chat_id = str(data.get("chat_id") or "")
    if chat_id:
        try:
            link = _data(client.request_json("POST", f"/im/v1/chats/{quote(chat_id, safe='')}/link"))
        except Exception:
            link = {}
        share_link = link.get("share_link")
        if share_link:
            result["share_link"] = share_link
    return result


def _cmd_im_chat_update(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    chat_id = str(getattr(args, "chat_id", "") or "").strip()
    if not chat_id:
        raise ValueError("specify --chat-id")
    body: dict[str, Any] = {}
    for attr in ("name", "description"):
        value = getattr(args, attr, None)
        if value is not None:
            body[attr] = str(value)
    owner = getattr(args, "owner", None)
    if owner is not None:
        body["owner_id"] = str(owner)
    if not body:
        raise ValueError("nothing to update")
    return _data(
        client.request_json(
            "PUT",
            f"/im/v1/chats/{quote(chat_id, safe='')}",
            params={"user_id_type": "open_id"},
            payload=body,
        )
    )


def _cmd_im_chat_messages_list(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    chat_id = str(getattr(args, "chat_id", "") or "").strip()
    if not chat_id:
        raise ValueError("specify --chat-id")
    params: dict[str, Any] = {
        "container_id_type": "chat",
        "container_id": chat_id,
        "card_msg_content_type": "raw_card_content",
    }
    page_size = getattr(args, "page_size", None)
    if page_size:
        params["page_size"] = int(page_size)
    sort = str(getattr(args, "sort", "") or "").strip().lower()
    if sort:
        params["sort_type"] = "ByCreateTimeDesc" if sort == "desc" else "ByCreateTimeAsc"
    return _data(client.request_json("GET", "/im/v1/messages", params=params))


def _cmd_im_threads_messages_list(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    thread_id = str(getattr(args, "thread", "") or getattr(args, "thread_id", "") or "").strip()
    if not thread_id:
        raise ValueError("specify --thread")
    params: dict[str, Any] = {
        "container_id_type": "thread",
        "container_id": thread_id,
        "card_msg_content_type": "raw_card_content",
    }
    page_size = getattr(args, "page_size", None)
    if page_size:
        params["page_size"] = int(page_size)
    sort = str(getattr(args, "sort", "") or "").strip().lower()
    if sort:
        params["sort_type"] = "ByCreateTimeDesc" if sort == "desc" else "ByCreateTimeAsc"
    return _data(client.request_json("GET", "/im/v1/messages", params=params))


def _cmd_im_messages_send(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    chat_id = str(getattr(args, "chat_id", "") or "").strip()
    user_id = str(getattr(args, "user_id", "") or "").strip()
    if bool(chat_id) == bool(user_id):
        raise ValueError("specify exactly one of --chat-id or --user-id")
    msg_type, content = _message_content(args)
    body: dict[str, Any] = {
        "receive_id": chat_id or user_id,
        "msg_type": msg_type,
        "content": content,
    }
    idempotency_key = str(getattr(args, "idempotency_key", "") or "").strip()
    if idempotency_key:
        body["uuid"] = idempotency_key
    data = _data(
        client.request_json(
            "POST",
            "/im/v1/messages",
            params={"receive_id_type": "chat_id" if chat_id else "open_id"},
            payload=body,
        )
    )
    return data


def _cmd_im_messages_reply(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    message_id = str(getattr(args, "message_id", "") or "").strip()
    if not message_id:
        raise ValueError("specify --message-id")
    msg_type, content = _message_content(args)
    body: dict[str, Any] = {"msg_type": msg_type, "content": content}
    if bool(getattr(args, "reply_in_thread", False)):
        body["reply_in_thread"] = True
    return _data(
        client.request_json(
            "POST",
            f"/im/v1/messages/{quote(message_id, safe='')}/reply",
            payload=body,
        )
    )


def _cmd_im_messages_mget(args: argparse.Namespace) -> Mapping[str, Any]:
    message_ids = _split_csv(getattr(args, "message_ids", None))
    if not message_ids:
        raise ValueError("specify --message-ids")
    client = _build_client(args)
    return _data(
        client.request_json(
            "GET",
            "/im/v1/messages/mget",
            params={"card_msg_content_type": "raw_card_content", "message_ids": message_ids},
        )
    )


def _quote_search_query(query: str) -> str:
    text = query.strip()
    if not text:
        return ""
    if " " not in text and "-" in text and not (text.startswith('"') and text.endswith('"')):
        return f'"{text}"'
    return text


def _cmd_im_chat_search(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    body: dict[str, Any] = {}
    query = _quote_search_query(str(getattr(args, "query", "") or ""))
    if query:
        body["query"] = query
    filter_payload: dict[str, Any] = {}
    search_types = _split_csv(getattr(args, "search_types", None))
    if search_types:
        filter_payload["search_types"] = search_types
    member_ids = _split_csv(getattr(args, "member_ids", None))
    if member_ids:
        filter_payload["member_ids"] = member_ids
    if filter_payload:
        body["filter"] = filter_payload
    sorter = str(getattr(args, "sort_by", "") or "").strip()
    if sorter:
        body["sorter"] = sorter
    params: dict[str, Any] = {}
    page_size = getattr(args, "page_size", None)
    if page_size:
        params["page_size"] = int(page_size)
    return _data(client.request_json("POST", "/im/v2/chats/search", params=params or None, payload=body))


def _cmd_im_messages_search(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    body: dict[str, Any] = {}
    query = str(getattr(args, "query", "") or "").strip()
    if query:
        body["query"] = query
    filter_payload: dict[str, Any] = {}
    chat_ids = _split_csv(getattr(args, "chat_id", None) or getattr(args, "chat_ids", None))
    if chat_ids:
        filter_payload["chat_ids"] = chat_ids
    sender_ids = _split_csv(getattr(args, "sender", None) or getattr(args, "sender_ids", None))
    if sender_ids:
        filter_payload["from_ids"] = sender_ids
    if bool(getattr(args, "is_at_me", False)):
        filter_payload["is_at_me"] = True
    at_chatter_ids = _split_csv(getattr(args, "at_chatter_ids", None))
    if at_chatter_ids:
        filter_payload["at_chatter_ids"] = at_chatter_ids
    if filter_payload:
        body["filter"] = filter_payload
    params: dict[str, Any] = {}
    page_size = getattr(args, "page_size", None)
    if page_size:
        params["page_size"] = int(page_size)
    data = _data(client.request_json("POST", "/im/v1/messages/search", params=params or None, payload=body))
    items = data.get("items")
    message_ids: list[str] = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, Mapping):
                continue
            meta = item.get("meta_data")
            meta_map = meta if isinstance(meta, Mapping) else item
            message_id = str(meta_map.get("message_id") or "")
            if message_id:
                message_ids.append(message_id)
    result = dict(data)
    if message_ids:
        result["messages"] = _data(
            client.request_json(
                "GET",
                "/im/v1/messages/mget",
                params={"card_msg_content_type": "raw_card_content", "message_ids": message_ids},
            )
        ).get("items", [])
    chat_ids_for_lookup: list[str] = []
    messages = result.get("messages")
    if isinstance(messages, list):
        for item in messages:
            if isinstance(item, Mapping):
                chat_id = str(item.get("chat_id") or "")
                if chat_id and chat_id not in chat_ids_for_lookup:
                    chat_ids_for_lookup.append(chat_id)
    if chat_ids_for_lookup:
        result["chats"] = _data(
            client.request_json(
                "POST",
                "/im/v1/chats/batch_query",
                payload={"chat_ids": chat_ids_for_lookup},
            )
        ).get("items", [])
    return result


def _filename_from_content_disposition(value: str) -> str:
    message = Message()
    message["content-disposition"] = value
    filename = message.get_filename()
    return filename or ""


def _cmd_im_messages_resources_download(args: argparse.Namespace) -> Mapping[str, Any]:
    client = _build_client(args)
    message_id = str(getattr(args, "message_id", "") or "").strip()
    file_key = str(getattr(args, "file_key", "") or "").strip()
    resource_type = str(getattr(args, "type", "") or "file").strip() or "file"
    if not message_id:
        raise ValueError("specify --message-id")
    if not file_key:
        raise ValueError("specify --file-key")
    output_dir = Path(str(getattr(args, "output", "") or ".")).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    base_url = str(getattr(client.config, "base_url", "") or "https://open.feishu.cn/open-apis").rstrip("/")
    url = (
        f"{base_url}/im/v1/messages/{quote(message_id, safe='')}/resources/"
        f"{quote(file_key, safe='')}?type={quote(resource_type, safe='')}"
    )
    headers = {"Authorization": f"Bearer {client.get_access_token()}"}
    with httpx.Client(timeout=getattr(client.config, "timeout_seconds", 30.0)) as http_client:
        try:
            response = http_client.get(url, headers=headers)
        except httpx.TimeoutException as exc:
            raise HTTPRequestError(f"http request timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise HTTPRequestError(f"http request failed: {exc}") from exc
    if response.status_code >= 400:
        raise HTTPRequestError(
            f"http request failed: {response.status_code}",
            status_code=response.status_code,
            response_text=response.text,
            response_headers=dict(response.headers),
        )
    filename = _filename_from_content_disposition(str(response.headers.get("content-disposition", "")))
    if not filename:
        filename = f"{file_key}.bin"
    target = output_dir / Path(filename).name
    target.write_bytes(response.content)
    return {
        "path": str(target),
        "filename": target.name,
        "content_type": response.headers.get("content-type"),
        "size_bytes": len(response.content),
    }


__all__ = [
    "_cmd_im_chat_create",
    "_cmd_im_chat_messages_list",
    "_cmd_im_chat_search",
    "_cmd_im_chat_update",
    "_cmd_im_messages_mget",
    "_cmd_im_messages_reply",
    "_cmd_im_messages_resources_download",
    "_cmd_im_messages_search",
    "_cmd_im_messages_send",
    "_cmd_im_threads_messages_list",
]
