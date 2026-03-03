from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

from ...im import MediaService, MessageService

from ..runtime import _build_client, _parse_json_array, _parse_json_object, _resolve_text_input

def _cmd_im_send_text(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    return service.send_text(
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        text=str(args.text),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_send_markdown(args: argparse.Namespace) -> Any:
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=getattr(args, "markdown_file", None),
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    service = MessageService(_build_client(args))
    return service.send_markdown(
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        markdown=markdown,
        locale=str(args.locale),
        title=getattr(args, "title", None),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_reply_markdown(args: argparse.Namespace) -> Any:
    markdown = _resolve_text_input(
        text=getattr(args, "markdown", None),
        file_path=getattr(args, "markdown_file", None),
        stdin_enabled=bool(getattr(args, "markdown_stdin", False)),
        name="markdown",
    )
    service = MessageService(_build_client(args))
    return service.reply_markdown(
        str(args.message_id),
        markdown,
        locale=str(args.locale),
        title=getattr(args, "title", None),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_send_generic(args: argparse.Namespace) -> Any:
    content = _parse_json_object(
        json_text=getattr(args, "content_json", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
        required=True,
    )
    service = MessageService(_build_client(args))
    return service.send(
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        msg_type=str(args.msg_type),
        content=content,
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_reply_generic(args: argparse.Namespace) -> Any:
    content = _parse_json_object(
        json_text=getattr(args, "content_json", None),
        file_path=getattr(args, "content_file", None),
        stdin_enabled=bool(getattr(args, "content_stdin", False)),
        name="content",
        required=True,
    )
    service = MessageService(_build_client(args))
    return service.reply(
        str(args.message_id),
        msg_type=str(args.msg_type),
        content=content,
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_get(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    return service.get(str(args.message_id))


def _cmd_im_recall(args: argparse.Namespace) -> Mapping[str, bool]:
    service = MessageService(_build_client(args))
    service.recall(str(args.message_id))
    return {"ok": True}


def _cmd_im_push_follow_up(args: argparse.Namespace) -> Any:
    follow_ups_raw = _parse_json_array(
        json_text=getattr(args, "follow_ups_json", None),
        file_path=getattr(args, "follow_ups_file", None),
        stdin_enabled=bool(getattr(args, "follow_ups_stdin", False)),
        name="follow-ups",
        required=True,
    )
    follow_ups: list[Mapping[str, Any]] = []
    for item in follow_ups_raw:
        if not isinstance(item, Mapping):
            raise ValueError("follow-ups must be a JSON array of objects")
        follow_ups.append({str(key): value for key, value in item.items()})
    service = MessageService(_build_client(args))
    return service.push_follow_up(str(args.message_id), follow_ups=follow_ups)


def _cmd_im_forward_thread(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    return service.forward_thread(
        str(args.thread_id),
        receive_id_type=str(args.receive_id_type),
        receive_id=str(args.receive_id),
        uuid=getattr(args, "uuid", None),
    )


def _cmd_im_update_url_previews(args: argparse.Namespace) -> Any:
    service = MessageService(_build_client(args))
    open_ids = list(getattr(args, "open_ids", []) or [])
    return service.batch_update_url_previews(
        preview_tokens=list(args.preview_tokens),
        open_ids=open_ids or None,
    )


def _cmd_media_upload_image(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MediaService(_build_client(args))
    return service.upload_image(str(args.path), image_type=str(args.image_type))


def _cmd_media_upload_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MediaService(_build_client(args))
    return service.upload_file(
        str(args.path),
        file_type=str(args.file_type),
        file_name=getattr(args, "file_name", None),
        duration=getattr(args, "duration", None),
        content_type=getattr(args, "content_type", None),
    )


def _cmd_media_download_file(args: argparse.Namespace) -> Mapping[str, Any]:
    service = MediaService(_build_client(args))
    file_key = str(args.file_key)
    message_id = getattr(args, "message_id", None)
    resource_type = getattr(args, "resource_type", None)
    mode = "file"

    if message_id:
        resolved_resource_type = str(resource_type or ("image" if file_key.startswith("img_") else "file"))
        content = service.download_message_resource(
            str(message_id),
            file_key,
            resource_type=resolved_resource_type,
        )
        mode = "message_resource"
    else:
        if resource_type:
            raise ValueError("--resource-type requires --message-id")
        if file_key.startswith("img_"):
            content = service.download_image(file_key)
            mode = "image"
        else:
            content = service.download_file(file_key)

    output_path = Path(str(args.output))
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(content)
    return {
        "ok": True,
        "file_key": file_key,
        "mode": mode,
        "message_id": str(message_id) if message_id else None,
        "output": str(output_path),
        "size": len(content),
    }


__all__ = [name for name in globals() if name.startswith("_cmd_")]
