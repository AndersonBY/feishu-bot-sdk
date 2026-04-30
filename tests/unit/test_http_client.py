import asyncio
from typing import Any, cast

import httpx

import pytest
from feishu_bot_sdk.exceptions import HTTPRequestError
from feishu_bot_sdk.http_client import AsyncJsonHttpClient, JsonHttpClient


class _Response:
    def __init__(self, status_code: int = 200, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {"ok": True}
        self.text = "{}"
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _SyncSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> _Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _Response()


class _AsyncSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request(self, method: str, url: str, **kwargs: Any) -> _Response:
        self.calls.append({"method": method, "url": url, **kwargs})
        return _Response()


class _TimeoutSyncSession:
    def request(self, method: str, url: str, **kwargs: Any) -> _Response:
        request = httpx.Request(method, url)
        raise httpx.ConnectTimeout("timed out", request=request)


class _TimeoutAsyncSession:
    async def request(self, method: str, url: str, **kwargs: Any) -> _Response:
        request = httpx.Request(method, url)
        raise httpx.ReadTimeout("timed out", request=request)


def test_json_http_client_omits_json_body_when_payload_is_none() -> None:
    session = _SyncSession()
    client = JsonHttpClient(session=cast(httpx.Client, session))

    client.request_json("DELETE", "https://example.com/tasks/1")

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["method"] == "DELETE"
    assert call["url"] == "https://example.com/tasks/1"
    assert "json" not in call


def test_json_http_client_includes_json_body_when_payload_is_present() -> None:
    session = _SyncSession()
    client = JsonHttpClient(session=cast(httpx.Client, session))

    client.request_json("PATCH", "https://example.com/tasks/1", payload={"status": "done"})

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["json"] == {"status": "done"}


def test_json_http_client_sends_multipart_files_and_form_data() -> None:
    session = _SyncSession()
    client = JsonHttpClient(session=cast(httpx.Client, session))

    client.request_json(
        "POST",
        "https://example.com/images",
        data={"image_type": "message"},
        files={"image": ("avatar.png", b"png-bytes", "image/png")},
    )

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["data"] == {"image_type": "message"}
    assert call["files"] == {"image": ("avatar.png", b"png-bytes", "image/png")}
    assert "json" not in call


def test_json_http_client_wraps_httpx_timeout_as_request_error() -> None:
    client = JsonHttpClient(session=cast(httpx.Client, _TimeoutSyncSession()))

    with pytest.raises(HTTPRequestError, match="http request timed out"):
        client.request_json("GET", "https://example.com/slow")


def test_async_json_http_client_omits_json_body_when_payload_is_none() -> None:
    session = _AsyncSession()
    client = AsyncJsonHttpClient(client=cast(httpx.AsyncClient, session))

    async def run() -> None:
        await client.request_json("DELETE", "https://example.com/tasks/1")

    asyncio.run(run())

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["method"] == "DELETE"
    assert "json" not in call


def test_async_json_http_client_includes_json_body_when_payload_is_present() -> None:
    session = _AsyncSession()
    client = AsyncJsonHttpClient(client=cast(httpx.AsyncClient, session))

    async def run() -> None:
        await client.request_json("POST", "https://example.com/tasks", payload={"summary": "demo"})

    asyncio.run(run())

    assert len(session.calls) == 1
    call = session.calls[0]
    assert call["json"] == {"summary": "demo"}


def test_async_json_http_client_wraps_httpx_timeout_as_request_error() -> None:
    client = AsyncJsonHttpClient(client=cast(httpx.AsyncClient, _TimeoutAsyncSession()))

    async def run() -> None:
        with pytest.raises(HTTPRequestError, match="http request timed out"):
            await client.request_json("GET", "https://example.com/slow")

    asyncio.run(run())
