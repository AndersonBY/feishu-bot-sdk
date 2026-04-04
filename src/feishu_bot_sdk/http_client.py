from typing import Any, Dict, Mapping, Optional

import httpx

from .exceptions import HTTPRequestError


class JsonHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        session: Optional[httpx.Client] = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._session = session or httpx.Client()

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, object]] = None,
        payload: Optional[Mapping[str, object]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        method_upper = method.upper()
        request_kwargs: dict[str, Any] = {
            "headers": dict(headers or {}),
            "params": dict(params or {}),
            "timeout": timeout_seconds or self._timeout_seconds,
        }
        if payload is not None and method_upper != "GET":
            request_kwargs["json"] = dict(payload)
        response = self._session.request(
            method_upper,
            url,
            **request_kwargs,
        )
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPRequestError("response body is not valid json") from exc
        if not isinstance(data, dict):
            raise HTTPRequestError("response body is not a json object")
        return data


class AsyncJsonHttpClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._client = client or httpx.AsyncClient()

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, object]] = None,
        payload: Optional[Mapping[str, object]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        method_upper = method.upper()
        request_kwargs: dict[str, Any] = {
            "headers": dict(headers or {}),
            "params": dict(params or {}),
            "timeout": timeout_seconds or self._timeout_seconds,
        }
        if payload is not None and method_upper != "GET":
            request_kwargs["json"] = dict(payload)
        response = await self._client.request(
            method_upper,
            url,
            **request_kwargs,
        )
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise HTTPRequestError("response body is not valid json") from exc
        if not isinstance(data, dict):
            raise HTTPRequestError("response body is not a json object")
        return data

    async def aclose(self) -> None:
        await self._client.aclose()
