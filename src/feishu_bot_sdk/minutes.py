from __future__ import annotations

from typing import Any, Mapping, Optional

import httpx

from .exceptions import HTTPRequestError
from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _extract_download_url(payload: Mapping[str, Any]) -> str:
    download_url = payload.get("download_url")
    if isinstance(download_url, str) and download_url.strip():
        return download_url.strip()
    raise ValueError("minute media response does not contain download_url")


class MinutesService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_minute(
        self,
        minute_token: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/minutes/v1/minutes/{minute_token}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    def get_minute_media_download_url(self, minute_token: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/minutes/v1/minutes/{minute_token}/media",
        )
        return _unwrap_data(response)

    def download_minute_media(self, minute_token: str) -> bytes:
        download_url = _extract_download_url(self.get_minute_media_download_url(minute_token))
        with httpx.Client(
            follow_redirects=True,
            timeout=self._client.config.timeout_seconds,
        ) as client:
            response = client.get(download_url)
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        return response.content


class AsyncMinutesService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_minute(
        self,
        minute_token: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/minutes/v1/minutes/{minute_token}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def get_minute_media_download_url(self, minute_token: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/minutes/v1/minutes/{minute_token}/media",
        )
        return _unwrap_data(response)

    async def download_minute_media(self, minute_token: str) -> bytes:
        download_url = _extract_download_url(await self.get_minute_media_download_url(minute_token))
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=self._client.config.timeout_seconds,
        ) as client:
            response = await client.get(download_url)
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        return response.content


__all__ = ["AsyncMinutesService", "MinutesService"]
