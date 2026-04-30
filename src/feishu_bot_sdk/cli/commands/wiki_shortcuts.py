from __future__ import annotations

import argparse
import time
from typing import Any, Mapping
from urllib.parse import quote

from ..runtime import _build_client
from ..runtime.risk import assert_risk_allowed


_WIKI_MY_LIBRARY_SPACE_ID = "my_library"


def _data(response: Mapping[str, Any]) -> dict[str, Any]:
    payload = response.get("data")
    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}
    return {}


def _node_payload(node: Any) -> dict[str, Any]:
    if not isinstance(node, Mapping):
        return {}
    result: dict[str, Any] = {}
    for key in (
        "space_id",
        "node_token",
        "obj_token",
        "obj_type",
        "parent_node_token",
        "node_type",
        "origin_node_token",
        "title",
        "has_child",
    ):
        if key in node:
            result[key] = node[key]
    return result


def _get_node(client: Any, token: str) -> dict[str, Any]:
    data = _data(client.request_json("GET", "/wiki/v2/spaces/get_node", params={"token": token}))
    node = data.get("node")
    if not isinstance(node, Mapping):
        raise ValueError("wiki node response missing node")
    return dict(node)


def _get_space(client: Any, space_id: str) -> dict[str, Any]:
    data = _data(client.request_json("GET", f"/wiki/v2/spaces/{quote(space_id, safe='')}"))
    space = data.get("space")
    if not isinstance(space, Mapping):
        raise ValueError("wiki space response missing space")
    return dict(space)


def _require_space_id_from_node(node: Mapping[str, Any]) -> str:
    space_id = str(node.get("space_id") or "").strip()
    if not space_id:
        raise ValueError("wiki node lookup returned no space_id")
    return space_id


def _is_bot_identity(args: argparse.Namespace) -> bool:
    return str(getattr(args, "auth_mode", "") or "").strip().lower() == "tenant"


def _node_create_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "node_type": str(getattr(args, "node_type", "") or "origin").strip() or "origin",
        "obj_type": str(getattr(args, "obj_type", "") or "docx").strip() or "docx",
    }
    title = str(getattr(args, "title", "") or "").strip()
    if title:
        body["title"] = title
    parent_node_token = str(getattr(args, "parent_node_token", "") or "").strip()
    if parent_node_token:
        body["parent_node_token"] = parent_node_token
    origin_node_token = str(getattr(args, "origin_node_token", "") or "").strip()
    if origin_node_token:
        body["origin_node_token"] = origin_node_token
    return body


def _resolve_create_space(client: Any, args: argparse.Namespace) -> tuple[str, str]:
    space_id = str(getattr(args, "space_id", "") or "").strip()
    parent_node_token = str(getattr(args, "parent_node_token", "") or "").strip()
    if _is_bot_identity(args) and space_id == _WIKI_MY_LIBRARY_SPACE_ID:
        raise ValueError("bot identity does not support --space-id my_library; use an explicit --space-id or --parent-node-token")
    if _is_bot_identity(args) and not space_id and not parent_node_token:
        raise ValueError("bot identity requires --space-id or --parent-node-token")
    if space_id and space_id != _WIKI_MY_LIBRARY_SPACE_ID:
        if parent_node_token:
            parent = _get_node(client, parent_node_token)
            parent_space_id = _require_space_id_from_node(parent)
            if parent_space_id != space_id:
                raise ValueError(f"--space-id {space_id!r} does not match parent node space {parent_space_id!r}")
        return space_id, "explicit_space_id"
    if parent_node_token:
        parent = _get_node(client, parent_node_token)
        return _require_space_id_from_node(parent), "parent_node_token"
    space = _get_space(client, _WIKI_MY_LIBRARY_SPACE_ID)
    resolved = str(space.get("space_id") or "").strip()
    if not resolved:
        raise ValueError("personal document library was not found, please specify --space-id")
    return resolved, "my_library"


def _validate_node_create(args: argparse.Namespace) -> None:
    node_type = str(getattr(args, "node_type", "") or "origin").strip()
    origin_node_token = str(getattr(args, "origin_node_token", "") or "").strip()
    if node_type == "shortcut" and not origin_node_token:
        raise ValueError("--origin-node-token is required when --node-type=shortcut")
    if node_type != "shortcut" and origin_node_token:
        raise ValueError("--origin-node-token can only be used when --node-type=shortcut")


def _resolve_move_spaces(client: Any, args: argparse.Namespace) -> tuple[str, str]:
    source_space_id = str(getattr(args, "source_space_id", "") or "").strip()
    target_space_id = str(getattr(args, "target_space_id", "") or "").strip()
    node_token = str(getattr(args, "node_token", "") or "").strip()
    target_parent_token = str(getattr(args, "target_parent_token", "") or "").strip()
    if not source_space_id:
        source_space_id = _require_space_id_from_node(_get_node(client, node_token))
    if target_parent_token:
        parent_space_id = _require_space_id_from_node(_get_node(client, target_parent_token))
        if not target_space_id:
            target_space_id = parent_space_id
        elif target_space_id != parent_space_id:
            raise ValueError(f"--target-space-id {target_space_id!r} does not match target parent node space {parent_space_id!r}")
    if not target_space_id:
        target_space_id = source_space_id
    return source_space_id, target_space_id


def _move_node_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {}
    target_parent_token = str(getattr(args, "target_parent_token", "") or "").strip()
    target_space_id = str(getattr(args, "target_space_id", "") or "").strip()
    if target_parent_token:
        body["target_parent_token"] = target_parent_token
    if target_space_id:
        body["target_space_id"] = target_space_id
    return body


def _docs_to_wiki_body(args: argparse.Namespace) -> dict[str, Any]:
    body: dict[str, Any] = {
        "obj_type": str(getattr(args, "obj_type", "") or "").strip(),
        "obj_token": str(getattr(args, "obj_token", "") or "").strip(),
    }
    target_parent_token = str(getattr(args, "target_parent_token", "") or "").strip()
    if target_parent_token:
        body["parent_wiki_token"] = target_parent_token
    if bool(getattr(args, "apply", False)):
        body["apply"] = True
    return body


def _validate_move(args: argparse.Namespace) -> str:
    node_token = str(getattr(args, "node_token", "") or "").strip()
    obj_type = str(getattr(args, "obj_type", "") or "").strip()
    obj_token = str(getattr(args, "obj_token", "") or "").strip()
    target_space_id = str(getattr(args, "target_space_id", "") or "").strip()
    apply = bool(getattr(args, "apply", False))
    if node_token:
        if obj_type or obj_token or apply:
            raise ValueError("--node-token cannot be combined with --obj-type, --obj-token, or --apply")
        if not target_space_id and not str(getattr(args, "target_parent_token", "") or "").strip():
            raise ValueError("--target-parent-token and --target-space-id cannot both be empty for wiki node move")
        return "node"
    if str(getattr(args, "source_space_id", "") or "").strip():
        raise ValueError("--source-space-id can only be used with --node-token")
    if not obj_type and not obj_token and not apply:
        raise ValueError("provide --node-token for wiki node move, or provide --obj-type and --obj-token for docs-to-wiki move")
    if not obj_type:
        raise ValueError("--obj-type is required for docs-to-wiki move")
    if not obj_token:
        raise ValueError("--obj-token is required for docs-to-wiki move")
    if not target_space_id:
        raise ValueError("--target-space-id is required for docs-to-wiki move")
    return "docs_to_wiki"


def _task_status(client: Any, task_id: str, task_type: str) -> dict[str, Any]:
    data = _data(client.request_json("GET", f"/wiki/v2/tasks/{quote(task_id, safe='')}", params={"task_type": task_type}))
    task = data.get("task")
    if not isinstance(task, Mapping):
        return {}
    return dict(task)


def _poll_move_task(client: Any, task_id: str, *, attempts: int, interval: float) -> tuple[dict[str, Any], bool]:
    task: dict[str, Any] = {}
    for attempt in range(max(attempts, 1)):
        if attempt:
            time.sleep(max(interval, 0.0))
        task = _task_status(client, task_id, "move")
        move_result = task.get("move_result")
        if not isinstance(move_result, list) or not move_result:
            continue
        if all(isinstance(item, Mapping) and int(item.get("status", 1) or 0) == 0 for item in move_result):
            return task, True
        if any(isinstance(item, Mapping) and int(item.get("status", 0) or 0) < 0 for item in move_result):
            return task, False
    return task, False


def _delete_task_status(task: Mapping[str, Any], task_id: str) -> dict[str, Any]:
    result = task.get("delete_space_result")
    result_map = result if isinstance(result, Mapping) else {}
    status = str(result_map.get("status") or "processing")
    status_msg = str(result_map.get("status_msg") or status)
    return {"task_id": str(task.get("task_id") or task_id), "status": status, "status_msg": status_msg}


def _poll_delete_space_task(client: Any, task_id: str, *, attempts: int, interval: float) -> tuple[dict[str, Any], bool]:
    status: dict[str, Any] = {"task_id": task_id, "status": "processing", "status_msg": "processing"}
    for attempt in range(max(attempts, 1)):
        if attempt:
            time.sleep(max(interval, 0.0))
        status = _delete_task_status(_task_status(client, task_id, "delete_space"), task_id)
        lowered = str(status.get("status") or "").strip().lower()
        if lowered == "success":
            return status, True
        if lowered in {"failure", "failed"}:
            return status, False
    return status, False


def _cmd_wiki_node_create(args: argparse.Namespace) -> Mapping[str, Any]:
    _validate_node_create(args)
    client = _build_client(args)
    space_id, resolved_by = _resolve_create_space(client, args)
    data = _data(
        client.request_json(
            "POST",
            f"/wiki/v2/spaces/{quote(space_id, safe='')}/nodes",
            payload=_node_create_body(args),
        )
    )
    node = data.get("node")
    node_out = _node_payload(node)
    return {
        "resolved_space_id": space_id,
        "resolved_by": resolved_by,
        **node_out,
    }


def _cmd_wiki_move(args: argparse.Namespace) -> Mapping[str, Any]:
    mode = _validate_move(args)
    client = _build_client(args)
    if mode == "node":
        source_space_id, target_space_id = _resolve_move_spaces(client, args)
        node_token = str(getattr(args, "node_token", "") or "").strip()
        data = _data(
            client.request_json(
                "POST",
                f"/wiki/v2/spaces/{quote(source_space_id, safe='')}/nodes/{quote(node_token, safe='')}/move",
                payload=_move_node_body(args),
            )
        )
        return {
            "mode": "node",
            "source_space_id": source_space_id,
            "target_space_id": target_space_id,
            **_node_payload(data.get("node")),
        }

    target_space_id = str(getattr(args, "target_space_id", "") or "").strip()
    data = _data(
        client.request_json(
            "POST",
            f"/wiki/v2/spaces/{quote(target_space_id, safe='')}/nodes/move_docs_to_wiki",
            payload=_docs_to_wiki_body(args),
        )
    )
    out: dict[str, Any] = {
        "mode": "docs_to_wiki",
        "obj_type": str(getattr(args, "obj_type", "") or "").strip(),
        "obj_token": str(getattr(args, "obj_token", "") or "").strip(),
        "target_space_id": target_space_id,
        "target_parent_token": str(getattr(args, "target_parent_token", "") or "").strip(),
    }
    wiki_token = str(data.get("wiki_token") or "")
    task_id = str(data.get("task_id") or "")
    if wiki_token:
        out.update({"ready": True, "failed": False, "wiki_token": wiki_token, "node_token": wiki_token})
        return out
    if bool(data.get("applied")):
        out.update({"ready": False, "failed": False, "applied": True, "status_msg": "move request submitted for approval"})
        return out
    if task_id:
        task, ready = _poll_move_task(
            client,
            task_id,
            attempts=int(getattr(args, "poll_attempts", 30) or 30),
            interval=float(getattr(args, "poll_interval", 2.0) or 2.0),
        )
        out.update({"task_id": task_id, "ready": ready})
        move_result = task.get("move_result")
        first = move_result[0] if isinstance(move_result, list) and move_result and isinstance(move_result[0], Mapping) else {}
        status = int(first.get("status", 1) or 0) if isinstance(first, Mapping) else 1
        out["failed"] = status < 0
        out["status"] = status
        out["status_msg"] = str(first.get("status_msg") or ("success" if ready else "processing")) if isinstance(first, Mapping) else "processing"
        if isinstance(first, Mapping):
            out.update(_node_payload(first.get("node")))
        if not ready:
            out["timed_out"] = True
            out["next_command"] = f"feishu drive +task_result --scenario wiki_move --task-id {task_id} --as {getattr(args, 'auth_mode', 'tenant')}"
        return out
    raise ValueError("move_docs_to_wiki returned neither wiki_token, task_id, nor applied result")


def _cmd_wiki_delete_space(args: argparse.Namespace) -> Mapping[str, Any]:
    assert_risk_allowed("high-risk-write", yes=bool(getattr(args, "yes", False)), command="wiki.+delete-space")
    client = _build_client(args)
    space_id = str(getattr(args, "space_id", "") or "").strip()
    if not space_id:
        raise ValueError("--space-id is required")
    data = _data(client.request_json("DELETE", f"/wiki/v2/spaces/{quote(space_id, safe='')}"))
    task_id = str(data.get("task_id") or "")
    out: dict[str, Any] = {"space_id": space_id}
    if not task_id:
        out.update({"ready": True, "failed": False, "status": "success", "status_msg": "success"})
        return out
    status, ready = _poll_delete_space_task(
        client,
        task_id,
        attempts=int(getattr(args, "poll_attempts", 30) or 30),
        interval=float(getattr(args, "poll_interval", 2.0) or 2.0),
    )
    out.update(
        {
            "task_id": task_id,
            "ready": ready,
            "failed": str(status.get("status") or "").strip().lower() in {"failure", "failed"},
            "status": status.get("status"),
            "status_msg": status.get("status_msg"),
        }
    )
    if not ready:
        out["timed_out"] = True
        out["next_command"] = f"feishu drive +task_result --scenario wiki_delete_space --task-id {task_id} --as {getattr(args, 'auth_mode', 'tenant')}"
    return out


__all__ = ["_cmd_wiki_delete_space", "_cmd_wiki_move", "_cmd_wiki_node_create"]
