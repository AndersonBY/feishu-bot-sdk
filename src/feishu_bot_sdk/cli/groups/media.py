from __future__ import annotations

from typing import Any

import click

from ..commands.messaging import (
    _cmd_media_download_file,
    _cmd_media_upload_file,
    _cmd_media_upload_image,
)
from ..context import build_cli_context, with_runtime_options


@click.group("media", help="Upload/download IM media files")
def media_group() -> None:
    pass


@media_group.command("upload-image")
@click.argument("path")
@click.option(
    "--image-type",
    default="message",
    show_default=True,
    type=click.Choice(["message", "avatar"]),
    help="Image type",
)
@with_runtime_options
def media_upload_image(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="media", media_command="upload-image", **params)
    cli_ctx.emit(_cmd_media_upload_image(args), cli_args=args)


@media_group.command("upload-file")
@click.argument("path")
@click.option(
    "--file-type",
    default="stream",
    show_default=True,
    type=click.Choice(["stream", "mp4", "pdf", "doc", "xls", "ppt", "opus"]),
    help="File type",
)
@click.option("--file-name", help="Override file name")
@click.option("--duration", type=int, help="Audio duration (ms)")
@click.option("--content-type", help="Override mime type")
@with_runtime_options
def media_upload_file(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="media", media_command="upload-file", **params)
    cli_ctx.emit(_cmd_media_upload_file(args), cli_args=args)


@media_group.command("download-file")
@click.argument("file_key")
@click.argument("output")
@click.option("--message-id", help="Download resource from this message via /im/v1/messages/{message_id}/resources/{file_key}")
@click.option(
    "--resource-type",
    type=click.Choice(["file", "image", "media"]),
    help="Resource type when --message-id is provided. Default inferred from key prefix.",
)
@with_runtime_options
def media_download_file(**kwargs: Any) -> None:
    cli_ctx, params = build_cli_context(kwargs)
    args = cli_ctx.build_args(group="media", media_command="download-file", **params)
    cli_ctx.emit(_cmd_media_download_file(args), cli_args=args)


__all__ = ["media_group"]
