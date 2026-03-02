import asyncio
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from urllib.parse import urlencode

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
class OAuthUserToken:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    refresh_expires_in: Optional[int] = None
    open_id: Optional[str] = None
    user_id: Optional[str] = None
    union_id: Optional[str] = None
    tenant_key: Optional[str] = None
    raw: Optional[Mapping[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "refresh_token": self.refresh_token,
            "refresh_expires_in": self.refresh_expires_in,
            "open_id": self.open_id,
            "user_id": self.user_id,
            "union_id": self.union_id,
            "tenant_key": self.tenant_key,
            "raw": dict(self.raw or {}),
        }


@dataclass
class OAuthUserInfo:
    open_id: Optional[str]
    user_id: Optional[str]
    union_id: Optional[str]
    name: Optional[str]
    en_name: Optional[str]
    avatar_url: Optional[str]
    email: Optional[str]
    mobile: Optional[str]
    tenant_key: Optional[str]
    raw: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "open_id": self.open_id,
            "user_id": self.user_id,
            "union_id": self.union_id,
            "name": self.name,
            "en_name": self.en_name,
            "avatar_url": self.avatar_url,
            "email": self.email,
            "mobile": self.mobile,
            "tenant_key": self.tenant_key,
            "raw": dict(self.raw),
        }


@dataclass
class _TokenCache:
    token: str
    expires_at: float


@dataclass
class _UserTokenCache:
    access_token: str
    expires_at: float
    refresh_token: Optional[str]
    refresh_expires_at: Optional[float]


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
        self._app_token_cache: Optional[_TokenCache] = None
        self._tenant_token_cache: Optional[_TokenCache] = None
        self._user_token_cache: Optional[_UserTokenCache] = _initial_user_token_cache(config)
        self._token_lock = threading.Lock()

    @property
    def config(self) -> FeishuConfig:
        return self._config

    def get_access_token(self) -> str:
        return self._resolve_access_token()

    def get_app_access_token(self) -> str:
        static_token = self._config.app_access_token
        if static_token:
            return static_token
        cached = self._app_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.token
        with self._token_lock:
            cached = self._app_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.token
            token = self._refresh_app_access_token()
            return token

    def build_authorize_url(
        self,
        *,
        redirect_uri: str,
        scope: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        if not self._config.app_id:
            raise ConfigurationError("app_id is required to build authorize url")
        query: dict[str, str] = {
            "app_id": self._config.app_id,
            "redirect_uri": redirect_uri,
        }
        if scope:
            query["scope"] = scope
        if state:
            query["state"] = state
        base_open_domain = _derive_open_domain(self._config.base_url)
        return f"{base_open_domain}/open-apis/authen/v1/authorize?{urlencode(query)}"

    def exchange_authorization_code(
        self,
        code: str,
        *,
        grant_type: str = "authorization_code",
    ) -> OAuthUserToken:
        payload = {
            "grant_type": grant_type,
            "code": code,
        }
        data = self._request_with_app_access_token("POST", "/authen/v1/access_token", payload=payload)
        token = _parse_user_token(data)
        self._update_user_token_cache(token)
        return token

    def refresh_user_access_token(self, refresh_token: Optional[str] = None) -> OAuthUserToken:
        token_to_use = refresh_token or _pick_refresh_token(self._config, self._user_token_cache)
        if not token_to_use:
            raise ConfigurationError("user refresh_token is required to refresh user access token")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": token_to_use,
        }
        data = self._request_with_app_access_token("POST", "/authen/v1/refresh_access_token", payload=payload)
        token = _parse_user_token(data)
        self._update_user_token_cache(token)
        return token

    def get_user_info(self, *, user_access_token: Optional[str] = None) -> OAuthUserInfo:
        token = user_access_token or self._resolve_user_access_token()
        data = self._request_with_bearer("GET", "/authen/v1/user_info", bearer_token=token)
        payload = data.get("data")
        if not isinstance(payload, Mapping):
            payload = {}
        return _parse_user_info(payload)

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
        token = self._resolve_access_token()
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

    def _resolve_access_token(self) -> str:
        if self._config.access_token:
            return self._config.access_token
        auth_mode = (self._config.auth_mode or "tenant").strip().lower()
        if auth_mode == "tenant":
            return self._resolve_tenant_access_token()
        if auth_mode == "user":
            return self._resolve_user_access_token()
        raise ConfigurationError("auth_mode must be either 'tenant' or 'user'")

    def _resolve_tenant_access_token(self) -> str:
        cached = self._tenant_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.token
        with self._token_lock:
            cached = self._tenant_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.token
            token = self._refresh_tenant_access_token()
            return token

    def _resolve_user_access_token(self) -> str:
        if self._config.user_access_token and self._config.user_refresh_token is None:
            return self._config.user_access_token

        cached = self._user_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.access_token
        with self._token_lock:
            cached = self._user_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.access_token
            token = self.refresh_user_access_token()
            return token.access_token

    def _refresh_app_access_token(self) -> str:
        if not self._config.app_id or not self._config.app_secret:
            raise ConfigurationError("app_id/app_secret is required to refresh app_access_token")
        url = f"{self._config.base_url}/auth/v3/app_access_token/internal"
        data = self._http.request_json(
            "POST",
            url,
            payload={"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu app token failed: {data}")
        token = data.get("app_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("feishu app token missing app_access_token")
        expires_in = int(data.get("expire") or 7200)
        self._app_token_cache = _TokenCache(token=token, expires_at=time.time() + expires_in)
        return token

    def _refresh_tenant_access_token(self) -> str:
        if not self._config.app_id or not self._config.app_secret:
            raise ConfigurationError("app_id/app_secret is required to refresh tenant-mode access token")
        url = f"{self._config.base_url}/auth/v3/tenant_access_token/internal"
        data = self._http.request_json(
            "POST",
            url,
            payload={"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu tenant token failed: {data}")
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("feishu tenant token response missing tenant_access_token")
        expires_in = int(data.get("expire") or 7200)
        self._tenant_token_cache = _TokenCache(token=token, expires_at=time.time() + expires_in)
        return token

    def _request_with_app_access_token(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, Any]:
        app_token = self.get_app_access_token()
        return self._request_with_bearer(
            method,
            path,
            payload=payload,
            params=params,
            bearer_token=app_token,
        )

    def _request_with_bearer(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
        bearer_token: str,
    ) -> Dict[str, Any]:
        method_upper = method.upper()
        url = f"{self._config.base_url}{path}"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        if method_upper != "GET":
            headers["Content-Type"] = "application/json"
        data = self._http.request_json(
            method_upper,
            url,
            headers=headers,
            params=dict(params or {}),
            payload=dict(payload or {}),
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu api failed: {data}")
        return data

    def _update_user_token_cache(self, token: OAuthUserToken) -> None:
        now = time.time()
        refresh_expires_at: Optional[float] = None
        if token.refresh_expires_in is not None and token.refresh_expires_in > 0:
            refresh_expires_at = now + token.refresh_expires_in
        self._user_token_cache = _UserTokenCache(
            access_token=token.access_token,
            expires_at=now + max(token.expires_in, 1),
            refresh_token=token.refresh_token,
            refresh_expires_at=refresh_expires_at,
        )


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
        self._app_token_cache: Optional[_TokenCache] = None
        self._tenant_token_cache: Optional[_TokenCache] = None
        self._user_token_cache: Optional[_UserTokenCache] = _initial_user_token_cache(config)
        self._token_lock = asyncio.Lock()

    @property
    def config(self) -> FeishuConfig:
        return self._config

    async def get_access_token(self) -> str:
        return await self._resolve_access_token()

    async def get_app_access_token(self) -> str:
        static_token = self._config.app_access_token
        if static_token:
            return static_token
        cached = self._app_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.token
        async with self._token_lock:
            cached = self._app_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.token
            token = await self._refresh_app_access_token()
            return token

    def build_authorize_url(
        self,
        *,
        redirect_uri: str,
        scope: Optional[str] = None,
        state: Optional[str] = None,
    ) -> str:
        if not self._config.app_id:
            raise ConfigurationError("app_id is required to build authorize url")
        query: dict[str, str] = {
            "app_id": self._config.app_id,
            "redirect_uri": redirect_uri,
        }
        if scope:
            query["scope"] = scope
        if state:
            query["state"] = state
        base_open_domain = _derive_open_domain(self._config.base_url)
        return f"{base_open_domain}/open-apis/authen/v1/authorize?{urlencode(query)}"

    async def exchange_authorization_code(
        self,
        code: str,
        *,
        grant_type: str = "authorization_code",
    ) -> OAuthUserToken:
        payload = {
            "grant_type": grant_type,
            "code": code,
        }
        data = await self._request_with_app_access_token("POST", "/authen/v1/access_token", payload=payload)
        token = _parse_user_token(data)
        self._update_user_token_cache(token)
        return token

    async def refresh_user_access_token(self, refresh_token: Optional[str] = None) -> OAuthUserToken:
        token_to_use = refresh_token or _pick_refresh_token(self._config, self._user_token_cache)
        if not token_to_use:
            raise ConfigurationError("user refresh_token is required to refresh user access token")
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": token_to_use,
        }
        data = await self._request_with_app_access_token("POST", "/authen/v1/refresh_access_token", payload=payload)
        token = _parse_user_token(data)
        self._update_user_token_cache(token)
        return token

    async def get_user_info(self, *, user_access_token: Optional[str] = None) -> OAuthUserInfo:
        token = user_access_token or await self._resolve_user_access_token()
        data = await self._request_with_bearer("GET", "/authen/v1/user_info", bearer_token=token)
        payload = data.get("data")
        if not isinstance(payload, Mapping):
            payload = {}
        return _parse_user_info(payload)

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
        token = await self._resolve_access_token()
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

    async def _resolve_access_token(self) -> str:
        if self._config.access_token:
            return self._config.access_token
        auth_mode = (self._config.auth_mode or "tenant").strip().lower()
        if auth_mode == "tenant":
            return await self._resolve_tenant_access_token()
        if auth_mode == "user":
            return await self._resolve_user_access_token()
        raise ConfigurationError("auth_mode must be either 'tenant' or 'user'")

    async def _resolve_tenant_access_token(self) -> str:
        cached = self._tenant_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.token
        async with self._token_lock:
            cached = self._tenant_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.token
            token = await self._refresh_tenant_access_token()
            return token

    async def _resolve_user_access_token(self) -> str:
        if self._config.user_access_token and self._config.user_refresh_token is None:
            return self._config.user_access_token

        cached = self._user_token_cache
        if cached and cached.expires_at > time.time() + 30:
            return cached.access_token
        async with self._token_lock:
            cached = self._user_token_cache
            if cached and cached.expires_at > time.time() + 30:
                return cached.access_token
            token = await self.refresh_user_access_token()
            return token.access_token

    async def _refresh_app_access_token(self) -> str:
        if not self._config.app_id or not self._config.app_secret:
            raise ConfigurationError("app_id/app_secret is required to refresh app_access_token")
        url = f"{self._config.base_url}/auth/v3/app_access_token/internal"
        data = await self._http.request_json(
            "POST",
            url,
            payload={"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu app token failed: {data}")
        token = data.get("app_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("feishu app token missing app_access_token")
        expires_in = int(data.get("expire") or 7200)
        self._app_token_cache = _TokenCache(token=token, expires_at=time.time() + expires_in)
        return token

    async def _refresh_tenant_access_token(self) -> str:
        if not self._config.app_id or not self._config.app_secret:
            raise ConfigurationError("app_id/app_secret is required to refresh tenant-mode access token")
        url = f"{self._config.base_url}/auth/v3/tenant_access_token/internal"
        data = await self._http.request_json(
            "POST",
            url,
            payload={"app_id": self._config.app_id, "app_secret": self._config.app_secret},
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu tenant token failed: {data}")
        token = data.get("tenant_access_token")
        if not isinstance(token, str) or not token:
            raise FeishuError("feishu tenant token response missing tenant_access_token")
        expires_in = int(data.get("expire") or 7200)
        self._tenant_token_cache = _TokenCache(token=token, expires_at=time.time() + expires_in)
        return token

    async def _request_with_app_access_token(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, Any]:
        app_token = await self.get_app_access_token()
        return await self._request_with_bearer(
            method,
            path,
            payload=payload,
            params=params,
            bearer_token=app_token,
        )

    async def _request_with_bearer(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
        bearer_token: str,
    ) -> Dict[str, Any]:
        method_upper = method.upper()
        url = f"{self._config.base_url}{path}"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        if method_upper != "GET":
            headers["Content-Type"] = "application/json"
        data = await self._http.request_json(
            method_upper,
            url,
            headers=headers,
            params=dict(params or {}),
            payload=dict(payload or {}),
            timeout_seconds=self._config.timeout_seconds,
        )
        if data.get("code") != 0:
            raise FeishuError(f"feishu api failed: {data}")
        return data

    def _update_user_token_cache(self, token: OAuthUserToken) -> None:
        now = time.time()
        refresh_expires_at: Optional[float] = None
        if token.refresh_expires_in is not None and token.refresh_expires_in > 0:
            refresh_expires_at = now + token.refresh_expires_in
        self._user_token_cache = _UserTokenCache(
            access_token=token.access_token,
            expires_at=now + max(token.expires_in, 1),
            refresh_token=token.refresh_token,
            refresh_expires_at=refresh_expires_at,
        )


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


def _derive_open_domain(base_url: str) -> str:
    marker = "/open-apis"
    index = base_url.find(marker)
    if index >= 0:
        return base_url[:index]
    return base_url.rstrip("/")


def _initial_user_token_cache(config: FeishuConfig) -> Optional[_UserTokenCache]:
    if not config.user_access_token:
        return None
    expires_at = float("inf")
    refresh_expires_at: Optional[float] = None
    if config.user_refresh_token:
        # Unknown exact expire time; force refresh soon for managed mode.
        expires_at = 0.0
    return _UserTokenCache(
        access_token=config.user_access_token,
        expires_at=expires_at,
        refresh_token=config.user_refresh_token,
        refresh_expires_at=refresh_expires_at,
    )


def _pick_refresh_token(config: FeishuConfig, cache: Optional[_UserTokenCache]) -> Optional[str]:
    if cache and cache.refresh_token:
        if cache.refresh_expires_at is None or cache.refresh_expires_at > time.time() + 30:
            return cache.refresh_token
    return config.user_refresh_token


def _parse_user_token(data: Mapping[str, Any]) -> OAuthUserToken:
    payload = data.get("data")
    if not isinstance(payload, Mapping):
        payload = {}
    access_token = payload.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise FeishuError(f"invalid oauth token response: {data}")
    token_type = payload.get("token_type")
    if not isinstance(token_type, str) or not token_type:
        token_type = "Bearer"
    expires_in = _to_int(payload.get("expires_in"), default=7200)
    return OAuthUserToken(
        access_token=access_token,
        token_type=token_type,
        expires_in=expires_in,
        refresh_token=_to_optional_str(payload.get("refresh_token")),
        refresh_expires_in=_to_optional_int(payload.get("refresh_expires_in")),
        open_id=_to_optional_str(payload.get("open_id")),
        user_id=_to_optional_str(payload.get("user_id")),
        union_id=_to_optional_str(payload.get("union_id")),
        tenant_key=_to_optional_str(payload.get("tenant_key")),
        raw=dict(payload),
    )


def _parse_user_info(payload: Mapping[str, Any]) -> OAuthUserInfo:
    return OAuthUserInfo(
        open_id=_to_optional_str(payload.get("open_id")),
        user_id=_to_optional_str(payload.get("user_id")),
        union_id=_to_optional_str(payload.get("union_id")),
        name=_to_optional_str(payload.get("name")),
        en_name=_to_optional_str(payload.get("en_name")),
        avatar_url=_to_optional_str(payload.get("avatar_url")),
        email=_to_optional_str(payload.get("email")),
        mobile=_to_optional_str(payload.get("mobile")),
        tenant_key=_to_optional_str(payload.get("tenant_key")),
        raw=dict(payload),
    )


def _to_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _to_int(value: Any, *, default: int) -> int:
    maybe = _to_optional_int(value)
    if maybe is None:
        return default
    return maybe


def _to_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            return None
    return None
