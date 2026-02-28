import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from .config import FeishuConfig
from .exceptions import ConfigurationError, FeishuError, HTTPRequestError
from .http_client import AsyncJsonHttpClient, JsonHttpClient
from .rate_limit import (
    AdaptiveRateLimiter,
    AsyncAdaptiveRateLimiter,
    RateLimitTuning,
    build_rate_limit_key,
)


@dataclass
class _TokenCache:
    token: str
    expires_at: float


class FeishuClient:
    def __init__(
        self,
        config: FeishuConfig,
        *,
        http_client: Optional[JsonHttpClient] = None,
        rate_limiter: Optional[AdaptiveRateLimiter] = None,
    ) -> None:
        self._config = config
        self._http = http_client or JsonHttpClient(timeout_seconds=config.timeout_seconds)
        self._rate_limiter = rate_limiter or _build_default_rate_limiter(config)
        self._tenant_token_cache: Optional[_TokenCache] = None
        self._token_lock = threading.Lock()

    @property
    def config(self) -> FeishuConfig:
        return self._config

    def get_tenant_access_token(self) -> str:
        return self._get_tenant_access_token()

    def send_text_message(self, receive_id: str, receive_id_type: str, text: str) -> None:
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        self.request_json(
            "POST",
            "/im/v1/messages",
            payload=payload,
            params={"receive_id_type": receive_id_type},
        )

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, Any]:
        token = self._get_tenant_access_token()
        url = f"{self._config.base_url}{path}"
        method_upper = method.upper()
        query_params = dict(params or {})
        json_payload = dict(payload or {})
        if method_upper == "GET" and not query_params:
            query_params = json_payload
            json_payload = {}
        headers = {"Authorization": f"Bearer {token}"}
        if method_upper != "GET":
            headers["Content-Type"] = "application/json"
        key = build_rate_limit_key(method_upper, path)
        if self._rate_limiter is not None:
            self._rate_limiter.acquire(key)
        try:
            data = self._http.request_json(
                method_upper,
                url,
                headers=headers,
                params=query_params,
                payload=json_payload,
                timeout_seconds=self._config.timeout_seconds,
            )
        except HTTPRequestError as exc:
            if self._rate_limiter is not None and exc.status_code == 429:
                self._rate_limiter.on_throttled(key, _extract_retry_after(exc.response_headers))
            raise
        if data.get("code") != 0:
            if self._rate_limiter is not None and _is_throttled_response(data):
                self._rate_limiter.on_throttled(key)
            raise FeishuError(f"feishu api failed: {data}")
        if self._rate_limiter is not None:
            self._rate_limiter.on_success(key)
        return data

    def _get_tenant_access_token(self) -> str:
        static_token = self._config.tenant_access_token
        if static_token:
            return static_token
        cached = self._tenant_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.token
        with self._token_lock:
            cached = self._tenant_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.token
            token = self._refresh_tenant_access_token()
            return token

    def _refresh_tenant_access_token(self) -> str:
        if not self._config.app_id or not self._config.app_secret:
            raise ConfigurationError("feishu app_id/app_secret is required")
        url = f"{self._config.base_url}/auth/v3/tenant_access_token/internal"
        data = self._http.request_json(
            "POST",
            url,
            payload={"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu token failed: {data}")
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("feishu token missing tenant_access_token")
        expires_in = int(data.get("expire") or 7200)
        self._tenant_token_cache = _TokenCache(
            token=token,
            expires_at=time.time() + expires_in,
        )
        return token


class AsyncFeishuClient:
    def __init__(
        self,
        config: FeishuConfig,
        *,
        http_client: Optional[AsyncJsonHttpClient] = None,
        rate_limiter: Optional[AsyncAdaptiveRateLimiter] = None,
    ) -> None:
        self._config = config
        self._http = http_client or AsyncJsonHttpClient(timeout_seconds=config.timeout_seconds)
        self._rate_limiter = rate_limiter or _build_default_async_rate_limiter(config)
        self._tenant_token_cache: Optional[_TokenCache] = None
        self._token_lock = asyncio.Lock()

    @property
    def config(self) -> FeishuConfig:
        return self._config

    async def get_tenant_access_token(self) -> str:
        return await self._get_tenant_access_token()

    async def send_text_message(self, receive_id: str, receive_id_type: str, text: str) -> None:
        payload = {
            "receive_id": receive_id,
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        }
        await self.request_json(
            "POST",
            "/im/v1/messages",
            payload=payload,
            params={"receive_id_type": receive_id_type},
        )

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, Any]:
        token = await self._get_tenant_access_token()
        url = f"{self._config.base_url}{path}"
        method_upper = method.upper()
        query_params = dict(params or {})
        json_payload = dict(payload or {})
        if method_upper == "GET" and not query_params:
            query_params = json_payload
            json_payload = {}
        headers = {"Authorization": f"Bearer {token}"}
        if method_upper != "GET":
            headers["Content-Type"] = "application/json"
        key = build_rate_limit_key(method_upper, path)
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire(key)
        try:
            data = await self._http.request_json(
                method_upper,
                url,
                headers=headers,
                params=query_params,
                payload=json_payload,
                timeout_seconds=self._config.timeout_seconds,
            )
        except HTTPRequestError as exc:
            if self._rate_limiter is not None and exc.status_code == 429:
                await self._rate_limiter.on_throttled(key, _extract_retry_after(exc.response_headers))
            raise
        if data.get("code") != 0:
            if self._rate_limiter is not None and _is_throttled_response(data):
                await self._rate_limiter.on_throttled(key)
            raise FeishuError(f"feishu api failed: {data}")
        if self._rate_limiter is not None:
            await self._rate_limiter.on_success(key)
        return data

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get_tenant_access_token(self) -> str:
        static_token = self._config.tenant_access_token
        if static_token:
            return static_token
        cached = self._tenant_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.token
        async with self._token_lock:
            cached = self._tenant_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.token
            token = await self._refresh_tenant_access_token()
            return token

    async def _refresh_tenant_access_token(self) -> str:
        if not self._config.app_id or not self._config.app_secret:
            raise ConfigurationError("feishu app_id/app_secret is required")
        url = f"{self._config.base_url}/auth/v3/tenant_access_token/internal"
        data = await self._http.request_json(
            "POST",
            url,
            payload={"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu token failed: {data}")
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("feishu token missing tenant_access_token")
        expires_in = int(data.get("expire") or 7200)
        self._tenant_token_cache = _TokenCache(
            token=token,
            expires_at=time.time() + expires_in,
        )
        return token


def _build_rate_tuning(config: FeishuConfig) -> RateLimitTuning:
    return RateLimitTuning(
        base_qps=config.rate_limit_base_qps,
        min_qps=config.rate_limit_min_qps,
        max_qps=config.rate_limit_max_qps,
        increase_factor=config.rate_limit_increase_factor,
        decrease_factor=config.rate_limit_decrease_factor,
        cooldown_seconds=config.rate_limit_cooldown_seconds,
        max_wait_seconds=config.rate_limit_max_wait_seconds,
    )


def _build_default_rate_limiter(config: FeishuConfig) -> Optional[AdaptiveRateLimiter]:
    if not config.rate_limit_enabled:
        return None
    return AdaptiveRateLimiter(_build_rate_tuning(config))


def _build_default_async_rate_limiter(config: FeishuConfig) -> Optional[AsyncAdaptiveRateLimiter]:
    if not config.rate_limit_enabled:
        return None
    return AsyncAdaptiveRateLimiter(_build_rate_tuning(config))


def _is_throttled_response(data: Mapping[str, object]) -> bool:
    code = data.get("code")
    if isinstance(code, int) and code in {99991663, 99991661, 11232}:
        return True
    message = data.get("msg")
    if not isinstance(message, str):
        return False
    lowered = message.lower()
    return "frequency" in lowered or "too many request" in lowered or "rate limit" in lowered


def _extract_retry_after(headers: Mapping[str, str]) -> Optional[float]:
    for key, value in headers.items():
        if key.lower() != "retry-after":
            continue
        stripped = value.strip()
        if not stripped:
            return None
        try:
            seconds = float(stripped)
        except ValueError:
            return None
        if seconds > 0:
            return seconds
    return None
