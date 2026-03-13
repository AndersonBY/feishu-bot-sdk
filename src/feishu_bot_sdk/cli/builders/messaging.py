from __future__ import annotations

import argparse

from ..commands import (
    _cmd_im_forward_thread,
    _cmd_im_get,
    _cmd_im_push_follow_up,
    _cmd_im_recall,
    _cmd_im_reply_generic,
    _cmd_im_reply_markdown,
    _cmd_im_send_generic,
    _cmd_im_send_markdown,
    _cmd_im_send_text,
    _cmd_im_update_url_previews,
    _cmd_media_download_file,
    _cmd_media_upload_file,
    _cmd_media_upload_image,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER
from .common import _add_receive_args

def _build_im_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    im_parser = subparsers.add_parser("im", help="Instant messaging")
    im_sub = im_parser.add_subparsers(dest="im_command")
    im_sub.required = True

    send_text = im_sub.add_parser("send-text", help="Send text message", parents=[shared])
    _add_receive_args(send_text)
    send_text.add_argument("--text", required=True, help="Text message body")
    send_text.add_argument("--uuid", help="Client message id for idempotency")
    send_text.set_defaults(handler=_cmd_im_send_text)

    send_markdown = im_sub.add_parser("send-markdown", help="Send markdown message", parents=[shared])
    _add_receive_args(send_markdown)
    send_markdown.add_argument("--markdown", help="Markdown text")
    send_markdown.add_argument("--markdown-file", help="Markdown file path")
    send_markdown.add_argument("--markdown-stdin", action="store_true", help="Read markdown text from stdin")
    send_markdown.add_argument("--locale", default="zh_cn", help="Locale key. Default: zh_cn")
    send_markdown.add_argument("--title", help="Post title")
    send_markdown.add_argument("--uuid", help="Client message id for idempotency")
    send_markdown.set_defaults(handler=_cmd_im_send_markdown)

    reply_markdown = im_sub.add_parser(
        "reply-markdown",
        help="Reply a markdown message by message_id",
        parents=[shared],
    )
    reply_markdown.add_argument("message_id", help="Original message_id")
    reply_markdown.add_argument("--markdown", help="Markdown text")
    reply_markdown.add_argument("--markdown-file", help="Markdown file path")
    reply_markdown.add_argument("--markdown-stdin", action="store_true", help="Read markdown text from stdin")
    reply_markdown.add_argument("--locale", default="zh_cn", help="Locale key. Default: zh_cn")
    reply_markdown.add_argument("--title", help="Post title")
    reply_markdown.add_argument("--uuid", help="Client message id for idempotency")
    reply_markdown.set_defaults(handler=_cmd_im_reply_markdown)

    send = im_sub.add_parser("send", help="Send generic message by msg_type + content", parents=[shared])
    _add_receive_args(send)
    send.add_argument("--msg-type", required=True, help="Feishu msg_type: text/image/interactive/share_chat/share_user/audio/media/file/sticker/post")
    send.add_argument("--content-json", help='Message content JSON, e.g. {"text":"Hello"} for text, {"image_key":"img_xxx"} for image')
    send.add_argument("--content-file", help="Message content JSON file path")
    send.add_argument("--content-stdin", action="store_true", help="Read message content JSON from stdin")
    send.add_argument("--uuid", help="Client message id for idempotency")
    send.set_defaults(handler=_cmd_im_send_generic)

    reply = im_sub.add_parser("reply", help="Reply generic message by msg_type + content", parents=[shared])
    reply.add_argument("message_id", help="Original message_id")
    reply.add_argument("--msg-type", required=True, help="Feishu msg_type: text/image/interactive/share_chat/share_user/audio/media/file/sticker/post")
    reply.add_argument("--content-json", help='Message content JSON, e.g. {"text":"Hello"} for text, {"image_key":"img_xxx"} for image')
    reply.add_argument("--content-file", help="Message content JSON file path")
    reply.add_argument("--content-stdin", action="store_true", help="Read message content JSON from stdin")
    reply.add_argument("--uuid", help="Client message id for idempotency")
    reply.set_defaults(handler=_cmd_im_reply_generic)

    get_message = im_sub.add_parser("get", help="Get message detail", parents=[shared])
    get_message.add_argument("message_id", help="message_id")
    get_message.set_defaults(handler=_cmd_im_get)

    recall = im_sub.add_parser("recall", help="Recall a message", parents=[shared])
    recall.add_argument("message_id", help="message_id")
    recall.set_defaults(handler=_cmd_im_recall)

    push_follow_up = im_sub.add_parser(
        "push-follow-up",
        help="Add follow-up bubbles below a message",
        parents=[shared],
    )
    push_follow_up.add_argument("message_id", help="message_id")
    push_follow_up.add_argument("--follow-ups-json", help='Follow-up list JSON array, e.g. [{"content":"Approve","i18n_contents":{"zh_cn":"批准"}}]')
    push_follow_up.add_argument("--follow-ups-file", help="Follow-up list JSON file path")
    push_follow_up.add_argument("--follow-ups-stdin", action="store_true", help="Read follow-up list JSON from stdin")
    push_follow_up.set_defaults(handler=_cmd_im_push_follow_up)

    forward_thread = im_sub.add_parser("forward-thread", help="Forward thread to target", parents=[shared])
    forward_thread.add_argument("thread_id", help="thread_id")
    _add_receive_args(forward_thread)
    forward_thread.add_argument("--uuid", help="Request uuid for deduplication")
    forward_thread.set_defaults(handler=_cmd_im_forward_thread)

    update_url_previews = im_sub.add_parser(
        "update-url-previews",
        help="Batch update URL previews",
        parents=[shared],
    )
    update_url_previews.add_argument(
        "--preview-token",
        action="append",
        dest="preview_tokens",
        required=True,
        help="Preview token from url.preview.get event, repeatable",
    )
    update_url_previews.add_argument(
        "--open-id",
        action="append",
        dest="open_ids",
        help="Optional open_id filter, repeatable",
    )
    update_url_previews.set_defaults(handler=_cmd_im_update_url_previews)

def _build_media_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    media_parser = subparsers.add_parser(
        "media",
        help="Media upload/download",
        description=(
            "Upload/download IM media.\n"
            "For resources from received messages, use --message-id with download-file."
        ),
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  feishu media upload-image ./demo.png --format json\n"
            "  feishu media download-file file_xxx ./downloads/file.bin --format json\n"
            "  feishu media download-file img_v3_xxx ./downloads/image.jpg --message-id om_xxx --resource-type image --auth-mode tenant --format json"
        ),
    )
    media_sub = media_parser.add_subparsers(dest="media_command")
    media_sub.required = True

    upload_image = media_sub.add_parser("upload-image", help="Upload image", parents=[shared])
    upload_image.add_argument("path", help="Image file path")
    upload_image.add_argument("--image-type", default="message", choices=("message", "avatar"), help="Image type (default: message)")
    upload_image.set_defaults(handler=_cmd_media_upload_image)

    upload_file = media_sub.add_parser("upload-file", help="Upload file", parents=[shared])
    upload_file.add_argument("path", help="File path")
    upload_file.add_argument("--file-type", default="stream", choices=("stream", "mp4", "pdf", "doc", "xls", "ppt", "opus"), help="File type (default: stream)")
    upload_file.add_argument("--file-name", help="Override file name")
    upload_file.add_argument("--duration", type=int, help="Audio duration (ms)")
    upload_file.add_argument("--content-type", help="Override mime type")
    upload_file.set_defaults(handler=_cmd_media_upload_file)

    download_file = media_sub.add_parser(
        "download-file",
        help="Download file/image by key (supports message resources)",
        parents=[shared],
    )
    download_file.add_argument("file_key", help="File key or image key")
    download_file.add_argument("output", help="Output file path")
    download_file.add_argument(
        "--message-id",
        help="If provided, download resource from this message via /im/v1/messages/{message_id}/resources/{file_key}",
    )
    download_file.add_argument(
        "--resource-type",
        choices=("file", "image", "media"),
        help="Resource type when --message-id is provided. Default inferred from key prefix.",
    )
    download_file.set_defaults(handler=_cmd_media_download_file)
