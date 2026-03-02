from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Mapping, Optional


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    return {}


def _as_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _as_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = _as_optional_str(item)
        if text is not None:
            items.append(text)
    return items


def _as_post_lines(value: Any) -> list[list[Mapping[str, Any]]]:
    if not isinstance(value, list):
        return []
    lines: list[list[Mapping[str, Any]]] = []
    for line in value:
        if not isinstance(line, list):
            continue
        nodes: list[Mapping[str, Any]] = []
        for node in line:
            if isinstance(node, Mapping):
                nodes.append({str(key): item for key, item in node.items()})
        lines.append(nodes)
    return lines


def _parse_content_json(content_raw: str) -> tuple[Mapping[str, Any], Optional[str]]:
    if not content_raw:
        return {}, None
    try:
        payload = json.loads(content_raw)
    except json.JSONDecodeError as exc:
        return {}, f"{type(exc).__name__}: {exc}"
    if not isinstance(payload, Mapping):
        return {}, "content is not a JSON object"
    return {str(key): value for key, value in payload.items()}, None


@dataclass(frozen=True)
class TextMessageContent:
    message_type: Literal["text"] = "text"
    text: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PostMessageContent:
    message_type: Literal["post"] = "post"
    title: Optional[str] = None
    content: list[list[Mapping[str, Any]]] = field(default_factory=list)
    locale: Optional[str] = None
    locales: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ImageMessageContent:
    message_type: Literal["image"] = "image"
    image_key: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FileMessageContent:
    message_type: Literal["file"] = "file"
    file_key: Optional[str] = None
    file_name: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FolderMessageContent:
    message_type: Literal["folder"] = "folder"
    file_key: Optional[str] = None
    file_name: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AudioMessageContent:
    message_type: Literal["audio"] = "audio"
    file_key: Optional[str] = None
    duration: Optional[int] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MediaMessageContent:
    message_type: Literal["media"] = "media"
    file_key: Optional[str] = None
    image_key: Optional[str] = None
    file_name: Optional[str] = None
    duration: Optional[int] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StickerMessageContent:
    message_type: Literal["sticker"] = "sticker"
    file_key: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InteractiveMessageContent:
    message_type: Literal["interactive"] = "interactive"
    title: Optional[str] = None
    elements: list[list[Mapping[str, Any]]] = field(default_factory=list)
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HongbaoMessageContent:
    message_type: Literal["hongbao"] = "hongbao"
    text: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CalendarMessageContent:
    message_type: str
    summary: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ShareChatMessageContent:
    message_type: Literal["share_chat"] = "share_chat"
    chat_id: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ShareUserMessageContent:
    message_type: Literal["share_user"] = "share_user"
    user_id: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SystemMessageContent:
    message_type: Literal["system"] = "system"
    template: Optional[str] = None
    from_user: list[str] = field(default_factory=list)
    to_chatters: list[str] = field(default_factory=list)
    divider_text: Mapping[str, Any] = field(default_factory=dict)
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LocationMessageContent:
    message_type: Literal["location"] = "location"
    name: Optional[str] = None
    longitude: Optional[str] = None
    latitude: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VideoChatMessageContent:
    message_type: Literal["video_chat"] = "video_chat"
    topic: Optional[str] = None
    start_time: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TodoMessageContent:
    message_type: Literal["todo"] = "todo"
    task_id: Optional[str] = None
    summary: Mapping[str, Any] = field(default_factory=dict)
    due_time: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VoteMessageContent:
    message_type: Literal["vote"] = "vote"
    topic: Optional[str] = None
    options: list[str] = field(default_factory=list)
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MergeForwardMessageContent:
    message_type: Literal["merge_forward"] = "merge_forward"
    content: Optional[str] = None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UnknownMessageContent:
    message_type: str
    content_raw: str
    raw: Mapping[str, Any] = field(default_factory=dict)
    parse_error: Optional[str] = None


ParsedMessageContent = (
    TextMessageContent
    | PostMessageContent
    | ImageMessageContent
    | FileMessageContent
    | FolderMessageContent
    | AudioMessageContent
    | MediaMessageContent
    | StickerMessageContent
    | InteractiveMessageContent
    | HongbaoMessageContent
    | CalendarMessageContent
    | ShareChatMessageContent
    | ShareUserMessageContent
    | SystemMessageContent
    | LocationMessageContent
    | VideoChatMessageContent
    | TodoMessageContent
    | VoteMessageContent
    | MergeForwardMessageContent
    | UnknownMessageContent
)


def _parse_text_message(_message_type: str, payload: Mapping[str, Any]) -> TextMessageContent:
    return TextMessageContent(
        text=_as_optional_str(payload.get("text")),
        raw=dict(payload),
    )


def _parse_post_message(_message_type: str, payload: Mapping[str, Any]) -> PostMessageContent:
    content = _as_post_lines(payload.get("content"))
    title = _as_optional_str(payload.get("title"))
    if content:
        return PostMessageContent(
            title=title,
            content=content,
            raw=dict(payload),
        )

    locales: dict[str, Mapping[str, Any]] = {}
    for key, value in payload.items():
        if isinstance(value, Mapping):
            locale_payload = {str(item_key): item for item_key, item in value.items()}
            if isinstance(locale_payload.get("content"), list):
                locales[str(key)] = locale_payload

    if not locales:
        return PostMessageContent(raw=dict(payload))

    locale = next(iter(locales))
    locale_payload = locales[locale]
    return PostMessageContent(
        title=_as_optional_str(locale_payload.get("title")),
        content=_as_post_lines(locale_payload.get("content")),
        locale=locale,
        locales=locales,
        raw=dict(payload),
    )


def _parse_image_message(_message_type: str, payload: Mapping[str, Any]) -> ImageMessageContent:
    return ImageMessageContent(
        image_key=_as_optional_str(payload.get("image_key")),
        raw=dict(payload),
    )


def _parse_file_message(_message_type: str, payload: Mapping[str, Any]) -> FileMessageContent:
    return FileMessageContent(
        file_key=_as_optional_str(payload.get("file_key")),
        file_name=_as_optional_str(payload.get("file_name")),
        raw=dict(payload),
    )


def _parse_folder_message(_message_type: str, payload: Mapping[str, Any]) -> FolderMessageContent:
    return FolderMessageContent(
        file_key=_as_optional_str(payload.get("file_key")),
        file_name=_as_optional_str(payload.get("file_name")),
        raw=dict(payload),
    )


def _parse_audio_message(_message_type: str, payload: Mapping[str, Any]) -> AudioMessageContent:
    return AudioMessageContent(
        file_key=_as_optional_str(payload.get("file_key")),
        duration=_as_optional_int(payload.get("duration")),
        raw=dict(payload),
    )


def _parse_media_message(_message_type: str, payload: Mapping[str, Any]) -> MediaMessageContent:
    return MediaMessageContent(
        file_key=_as_optional_str(payload.get("file_key")),
        image_key=_as_optional_str(payload.get("image_key")),
        file_name=_as_optional_str(payload.get("file_name")),
        duration=_as_optional_int(payload.get("duration")),
        raw=dict(payload),
    )


def _parse_sticker_message(_message_type: str, payload: Mapping[str, Any]) -> StickerMessageContent:
    return StickerMessageContent(
        file_key=_as_optional_str(payload.get("file_key")),
        raw=dict(payload),
    )


def _parse_interactive_message(_message_type: str, payload: Mapping[str, Any]) -> InteractiveMessageContent:
    return InteractiveMessageContent(
        title=_as_optional_str(payload.get("title")),
        elements=_as_post_lines(payload.get("elements")),
        raw=dict(payload),
    )


def _parse_hongbao_message(_message_type: str, payload: Mapping[str, Any]) -> HongbaoMessageContent:
    return HongbaoMessageContent(
        text=_as_optional_str(payload.get("text")),
        raw=dict(payload),
    )


def _parse_calendar_message(message_type: str, payload: Mapping[str, Any]) -> CalendarMessageContent:
    calendar_type = message_type if message_type in {"share_calendar_event", "calendar", "general_calendar"} else "calendar"
    return CalendarMessageContent(
        message_type=calendar_type,
        summary=_as_optional_str(payload.get("summary")),
        start_time=_as_optional_str(payload.get("start_time")),
        end_time=_as_optional_str(payload.get("end_time")),
        raw=dict(payload),
    )


def _parse_share_chat_message(_message_type: str, payload: Mapping[str, Any]) -> ShareChatMessageContent:
    return ShareChatMessageContent(
        chat_id=_as_optional_str(payload.get("chat_id")),
        raw=dict(payload),
    )


def _parse_share_user_message(_message_type: str, payload: Mapping[str, Any]) -> ShareUserMessageContent:
    return ShareUserMessageContent(
        user_id=_as_optional_str(payload.get("user_id")),
        raw=dict(payload),
    )


def _parse_system_message(_message_type: str, payload: Mapping[str, Any]) -> SystemMessageContent:
    return SystemMessageContent(
        template=_as_optional_str(payload.get("template")),
        from_user=_as_string_list(payload.get("from_user")),
        to_chatters=_as_string_list(payload.get("to_chatters")),
        divider_text=_as_mapping(payload.get("divider_text")),
        raw=dict(payload),
    )


def _parse_location_message(_message_type: str, payload: Mapping[str, Any]) -> LocationMessageContent:
    return LocationMessageContent(
        name=_as_optional_str(payload.get("name")),
        longitude=_as_optional_str(payload.get("longitude")),
        latitude=_as_optional_str(payload.get("latitude")),
        raw=dict(payload),
    )


def _parse_video_chat_message(_message_type: str, payload: Mapping[str, Any]) -> VideoChatMessageContent:
    return VideoChatMessageContent(
        topic=_as_optional_str(payload.get("topic")),
        start_time=_as_optional_str(payload.get("start_time")),
        raw=dict(payload),
    )


def _parse_todo_message(_message_type: str, payload: Mapping[str, Any]) -> TodoMessageContent:
    return TodoMessageContent(
        task_id=_as_optional_str(payload.get("task_id")),
        summary=_as_mapping(payload.get("summary")),
        due_time=_as_optional_str(payload.get("due_time")),
        raw=dict(payload),
    )


def _parse_vote_message(_message_type: str, payload: Mapping[str, Any]) -> VoteMessageContent:
    return VoteMessageContent(
        topic=_as_optional_str(payload.get("topic")),
        options=_as_string_list(payload.get("options")),
        raw=dict(payload),
    )


def _parse_merge_forward_message(_message_type: str, payload: Mapping[str, Any]) -> MergeForwardMessageContent:
    return MergeForwardMessageContent(
        content=_as_optional_str(payload.get("content")),
        raw=dict(payload),
    )


_PARSER_TABLE: dict[str, Callable[[str, Mapping[str, Any]], ParsedMessageContent]] = {
    "text": _parse_text_message,
    "post": _parse_post_message,
    "image": _parse_image_message,
    "file": _parse_file_message,
    "folder": _parse_folder_message,
    "audio": _parse_audio_message,
    "media": _parse_media_message,
    "sticker": _parse_sticker_message,
    "interactive": _parse_interactive_message,
    "hongbao": _parse_hongbao_message,
    "share_calendar_event": _parse_calendar_message,
    "calendar": _parse_calendar_message,
    "general_calendar": _parse_calendar_message,
    "share_chat": _parse_share_chat_message,
    "share_user": _parse_share_user_message,
    "system": _parse_system_message,
    "location": _parse_location_message,
    "video_chat": _parse_video_chat_message,
    "todo": _parse_todo_message,
    "vote": _parse_vote_message,
    "merge_forward": _parse_merge_forward_message,
}


def parse_received_message_content(
    *,
    message_type: Optional[str],
    content_raw: str,
) -> ParsedMessageContent:
    normalized_type = (message_type or "").strip().lower()
    payload, parse_error = _parse_content_json(content_raw)
    parser = _PARSER_TABLE.get(normalized_type)
    if parser is None:
        return UnknownMessageContent(
            message_type=normalized_type or "unknown",
            content_raw=content_raw,
            raw=payload,
            parse_error=parse_error,
        )
    if parse_error is not None:
        return UnknownMessageContent(
            message_type=normalized_type,
            content_raw=content_raw,
            raw=payload,
            parse_error=parse_error,
        )
    return parser(normalized_type, payload)


def extract_text_from_parsed_message(content: ParsedMessageContent) -> Optional[str]:
    if isinstance(content, TextMessageContent):
        return content.text
    if isinstance(content, HongbaoMessageContent):
        return content.text
    return None
