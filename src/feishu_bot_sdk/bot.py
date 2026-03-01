from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
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


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = _as_optional_str(item)
        if text is not None:
            result.append(text)
    return result


@dataclass(frozen=True)
class BotInfo:
    activate_status: Optional[int]
    app_name: Optional[str]
    avatar_url: Optional[str]
    ip_white_list: list[str]
    open_id: Optional[str]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_raw(cls, payload: Mapping[str, Any]) -> "BotInfo":
        return cls(
            activate_status=_as_optional_int(payload.get("activate_status")),
            app_name=_as_optional_str(payload.get("app_name")),
            avatar_url=_as_optional_str(payload.get("avatar_url")),
            ip_white_list=_as_str_list(payload.get("ip_white_list")),
            open_id=_as_optional_str(payload.get("open_id")),
            raw=dict(payload),
        )


@dataclass(frozen=True)
class BotInfoResponse:
    code: int
    msg: Optional[str]
    bot: Optional[BotInfo]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.code == 0

    @classmethod
    def from_raw(cls, payload: Mapping[str, Any]) -> "BotInfoResponse":
        bot_payload = _as_mapping(payload.get("bot"))
        return cls(
            code=_as_optional_int(payload.get("code")) or 0,
            msg=_as_optional_str(payload.get("msg")),
            bot=BotInfo.from_raw(bot_payload) if bot_payload else None,
            raw=dict(payload),
        )


class BotService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_info(self) -> BotInfoResponse:
        response = self._client.request_json("GET", "/bot/v3/info")
        return BotInfoResponse.from_raw(response)


class AsyncBotService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_info(self) -> BotInfoResponse:
        response = await self._client.request_json("GET", "/bot/v3/info")
        return BotInfoResponse.from_raw(response)
