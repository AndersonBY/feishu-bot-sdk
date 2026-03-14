from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient


def _as_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


# ---------------------------------------------------------------------------
# Typed responses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CardKitResponse:
    code: int
    msg: Optional[str]
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.code == 0

    @classmethod
    def from_raw(cls, payload: Mapping[str, Any]) -> CardKitResponse:
        code = payload.get("code")
        if not isinstance(code, int):
            code = 0
        return cls(
            code=code,
            msg=_as_optional_str(payload.get("msg")),
            raw=dict(payload),
        )


@dataclass(frozen=True)
class CardKitCreateResponse(CardKitResponse):
    card_id: Optional[str] = None

    @classmethod
    def from_raw(cls, payload: Mapping[str, Any]) -> CardKitCreateResponse:
        code = payload.get("code")
        if not isinstance(code, int):
            code = 0
        data = payload.get("data")
        if not isinstance(data, Mapping):
            data = {}
        card_id = _as_optional_str(data.get("card_id")) or _as_optional_str(payload.get("card_id"))
        return cls(
            code=code,
            msg=_as_optional_str(payload.get("msg")),
            raw=dict(payload),
            card_id=card_id,
        )


# ---------------------------------------------------------------------------
# CardKit API paths
# ---------------------------------------------------------------------------

_CARDKIT_BASE = "/cardkit/v1"


def _card_create_path() -> str:
    return f"{_CARDKIT_BASE}/cards"


def _card_update_path(card_id: str) -> str:
    return f"{_CARDKIT_BASE}/cards/{card_id}"


def _card_element_content_path(card_id: str, element_id: str) -> str:
    return f"{_CARDKIT_BASE}/cards/{card_id}/elements/{element_id}/content"


def _card_settings_path(card_id: str) -> str:
    return f"{_CARDKIT_BASE}/cards/{card_id}/settings"


# ---------------------------------------------------------------------------
# Sync service
# ---------------------------------------------------------------------------


class CardKitService:
    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    def create(
        self,
        *,
        card: Mapping[str, Any],
        type: str = "card_json",
    ) -> CardKitCreateResponse:
        payload = {
            "type": type,
            "data": json.dumps(card, ensure_ascii=False) if isinstance(card, Mapping) else card,
        }
        data = self._client.request_json("POST", _card_create_path(), payload=payload)
        return CardKitCreateResponse.from_raw(data)

    def update(
        self,
        card_id: str,
        *,
        card: Mapping[str, Any],
        sequence: int,
    ) -> CardKitResponse:
        payload = {
            "card": {
                "type": "card_json",
                "data": json.dumps(card, ensure_ascii=False),
            },
            "sequence": sequence,
        }
        data = self._client.request_json("PUT", _card_update_path(card_id), payload=payload)
        return CardKitResponse.from_raw(data)

    def set_element_content(
        self,
        card_id: str,
        *,
        element_id: str,
        content: str,
        sequence: int,
    ) -> CardKitResponse:
        payload = {"content": content, "sequence": sequence}
        data = self._client.request_json(
            "PUT",
            _card_element_content_path(card_id, element_id),
            payload=payload,
        )
        return CardKitResponse.from_raw(data)

    def set_settings(
        self,
        card_id: str,
        *,
        settings: Mapping[str, Any],
        sequence: int,
    ) -> CardKitResponse:
        payload = {
            "settings": json.dumps(settings, ensure_ascii=False),
            "sequence": sequence,
        }
        data = self._client.request_json("PATCH", _card_settings_path(card_id), payload=payload)
        return CardKitResponse.from_raw(data)

    def set_streaming_mode(
        self,
        card_id: str,
        *,
        enabled: bool,
        sequence: int,
    ) -> CardKitResponse:
        return self.set_settings(
            card_id,
            settings={"config": {"streaming_mode": enabled}},
            sequence=sequence,
        )


# ---------------------------------------------------------------------------
# Async service
# ---------------------------------------------------------------------------


class AsyncCardKitService:
    def __init__(self, client: AsyncFeishuClient) -> None:
        self._client = client

    async def create(
        self,
        *,
        card: Mapping[str, Any],
        type: str = "card_json",
    ) -> CardKitCreateResponse:
        payload = {
            "type": type,
            "data": json.dumps(card, ensure_ascii=False) if isinstance(card, Mapping) else card,
        }
        data = await self._client.request_json("POST", _card_create_path(), payload=payload)
        return CardKitCreateResponse.from_raw(data)

    async def update(
        self,
        card_id: str,
        *,
        card: Mapping[str, Any],
        sequence: int,
    ) -> CardKitResponse:
        payload = {
            "card": {
                "type": "card_json",
                "data": json.dumps(card, ensure_ascii=False),
            },
            "sequence": sequence,
        }
        data = await self._client.request_json("PUT", _card_update_path(card_id), payload=payload)
        return CardKitResponse.from_raw(data)

    async def set_element_content(
        self,
        card_id: str,
        *,
        element_id: str,
        content: str,
        sequence: int,
    ) -> CardKitResponse:
        payload = {"content": content, "sequence": sequence}
        data = await self._client.request_json(
            "PUT",
            _card_element_content_path(card_id, element_id),
            payload=payload,
        )
        return CardKitResponse.from_raw(data)

    async def set_settings(
        self,
        card_id: str,
        *,
        settings: Mapping[str, Any],
        sequence: int,
    ) -> CardKitResponse:
        payload = {
            "settings": json.dumps(settings, ensure_ascii=False),
            "sequence": sequence,
        }
        data = await self._client.request_json("PATCH", _card_settings_path(card_id), payload=payload)
        return CardKitResponse.from_raw(data)

    async def set_streaming_mode(
        self,
        card_id: str,
        *,
        enabled: bool,
        sequence: int,
    ) -> CardKitResponse:
        return await self.set_settings(
            card_id,
            settings={"config": {"streaming_mode": enabled}},
            sequence=sequence,
        )
