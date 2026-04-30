import asyncio
from typing import Any, cast

from feishu_bot_sdk.config import FeishuConfig
from feishu_bot_sdk.exceptions import FeishuError, HTTPRequestError
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient, _initial_user_token_cache
from feishu_bot_sdk.http_client import AsyncJsonHttpClient, JsonHttpClient


class _HttpClientStub:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, timeout_seconds
        call = {
            "method": method,
            "url": url,
            "headers": dict(headers or {}),
            "payload": dict(payload or {}),
        }
        self.calls.append(call)
        if url.endswith("/authen/v1/user_info"):
            bearer = call["headers"].get("Authorization", "")
            if bearer == "Bearer stale-access":
                raise FeishuError("feishu api failed: {'code': 99991663, 'msg': 'invalid access token'}")
            if bearer == "Bearer fresh-access":
                return {
                    "code": 0,
                    "data": {
                        "open_id": "ou_test",
                        "user_id": "u_test",
                        "union_id": "on_test",
                        "name": "Tester",
                    },
                }
        if url.endswith("/auth/v3/app_access_token/internal"):
            return {"code": 0, "app_access_token": "app-token", "expire": 7200}
        if url.endswith("/authen/v1/refresh_access_token"):
            assert payload == {"grant_type": "refresh_token", "refresh_token": "refresh-token"}
            return {
                "code": 0,
                "data": {
                    "access_token": "fresh-access",
                    "token_type": "Bearer",
                    "expires_in": 7200,
                    "refresh_token": "refresh-token-2",
                    "refresh_expires_in": 86400,
                },
            }
        raise AssertionError(f"unexpected request: {method} {url}")


class _CaptureHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        data: dict[str, object] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "payload": payload,
                "data": data,
                "files": files,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {"code": 0, "data": {}}


class _PermissionHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("permission errors must not trigger user token refresh")
        return {
            "code": 99991672,
            "msg": (
                "Unauthorized. You do not have permission to perform the requested operation on the resource. "
                "Please request user re-authorization and try again."
            ),
            "data": {},
        }


class _BusinessTokenHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("business token errors must not trigger user token refresh")
        return {"code": 4000002, "msg": "invalid docs token", "data": {}}


class _HTTPPermissionHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("permission HTTP errors must not trigger user token refresh")
        raise HTTPRequestError(
            "http request failed: 400",
            status_code=400,
            response_text=(
                '{"code":99991672,"msg":"Unauthorized. You do not have permission to perform the '
                'requested operation on the resource. Please request user re-authorization and try again."}'
            ),
        )


class _HTTPBusinessTokenFieldHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("business token field errors must not trigger user token refresh")
        raise HTTPRequestError(
            "http request failed: 400",
            status_code=400,
            response_text=(
                '{"code":99992402,"msg":"field validation failed","error":{"field_violations":'
                '[{"field":"minute_token","description":"the min len is 24"}]}}'
            ),
        )


class _AsyncPermissionHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("permission errors must not trigger user token refresh")
        return {
            "code": 99991672,
            "msg": (
                "Unauthorized. You do not have permission to perform the requested operation on the resource. "
                "Please request user re-authorization and try again."
            ),
            "data": {},
        }


class _AsyncBusinessTokenHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("business token errors must not trigger user token refresh")
        return {"code": 4000002, "msg": "invalid docs token", "data": {}}


class _AsyncHTTPPermissionHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        del params, payload, timeout_seconds
        self.calls.append({"method": method, "url": url, "headers": dict(headers or {})})
        if url.endswith("/auth/v3/app_access_token/internal") or url.endswith("/authen/v1/refresh_access_token"):
            raise AssertionError("permission HTTP errors must not trigger user token refresh")
        raise HTTPRequestError(
            "http request failed: 400",
            status_code=400,
            response_text=(
                '{"code":99991672,"msg":"Unauthorized. You do not have permission to perform the '
                'requested operation on the resource. Please request user re-authorization and try again."}'
            ),
        )


class _AsyncCaptureHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, object] | None = None,
        payload: dict[str, object] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {"code": 0, "data": {}}


def test_initial_user_token_cache_keeps_access_token_when_expiry_unknown() -> None:
    cache = _initial_user_token_cache(
        FeishuConfig(
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        )
    )

    assert cache is not None
    assert cache.access_token == "access-token"
    assert cache.refresh_token == "refresh-token"
    assert cache.expires_at == float("inf")


def test_get_user_info_refreshes_only_after_token_failure() -> None:
    http = _HttpClientStub()
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="stale-access",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    info = client.get_user_info()

    assert info.open_id == "ou_test"
    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == [
        "/authen/v1/user_info",
        "/auth/v3/app_access_token/internal",
        "/authen/v1/refresh_access_token",
        "/authen/v1/user_info",
    ]
    assert http.calls[0]["headers"]["Authorization"] == "Bearer stale-access"
    assert http.calls[-1]["headers"]["Authorization"] == "Bearer fresh-access"


def test_request_json_does_not_refresh_on_reauthorization_permission_error() -> None:
    http = _PermissionHttpClient()
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    try:
        client.request_json("POST", "/base/v3/bases", payload={"name": "Denied"})
    except FeishuError as exc:
        assert "99991672" in str(exc)
    else:
        raise AssertionError("expected FeishuError")

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/base/v3/bases"]


def test_request_json_does_not_refresh_on_http_unauthorized_permission_error() -> None:
    http = _HTTPPermissionHttpClient()
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    try:
        client.request_json("POST", "/base/v3/bases", payload={"name": "Denied"})
    except HTTPRequestError as exc:
        assert exc.status_code == 400
        assert "99991672" in str(exc.response_text)
    else:
        raise AssertionError("expected HTTPRequestError")

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/base/v3/bases"]


def test_request_json_does_not_refresh_on_http_business_token_field_error() -> None:
    http = _HTTPBusinessTokenFieldHttpClient()
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    try:
        client.request_json("GET", "/minutes/v1/minutes/invalid_minute/media")
    except HTTPRequestError as exc:
        assert exc.status_code == 400
        assert "minute_token" in str(exc.response_text)
    else:
        raise AssertionError("expected HTTPRequestError")

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/minutes/v1/minutes/invalid_minute/media"]


def test_request_json_does_not_refresh_on_business_object_token_error() -> None:
    http = _BusinessTokenHttpClient()
    client = FeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    try:
        client.request_json("GET", "/docs/v1/content", params={"doc_token": "missing_doc"})
    except FeishuError as exc:
        assert "invalid docs token" in str(exc)
    else:
        raise AssertionError("expected FeishuError")

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/docs/v1/content"]


def test_request_json_uses_openapi_root_for_full_openapi_paths_and_keeps_delete_payload_none() -> None:
    http = _CaptureHttpClient()
    client = FeishuClient(
        FeishuConfig(
            auth_mode="tenant",
            access_token="tenant-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    client.request_json("DELETE", "/open-apis/task/v2/tasks/task_1")

    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == "https://open.feishu.cn/open-apis/task/v2/tasks/task_1"
    assert call["payload"] is None


def test_request_multipart_uses_openapi_root_and_omits_json_content_type() -> None:
    http = _CaptureHttpClient()
    client = FeishuClient(
        FeishuConfig(
            auth_mode="tenant",
            access_token="tenant-token",
        ),
        http_client=cast(JsonHttpClient, http),
    )

    client.request_multipart(
        "POST",
        "/open-apis/im/v1/images",
        data={"image_type": "message"},
        files={"image": ("avatar.png", b"png-bytes", "image/png")},
    )

    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == "https://open.feishu.cn/open-apis/im/v1/images"
    assert call["data"] == {"image_type": "message"}
    assert call["files"] == {"image": ("avatar.png", b"png-bytes", "image/png")}
    assert call["headers"] == {"Authorization": "Bearer tenant-token"}


def test_async_request_json_uses_openapi_root_for_full_openapi_paths_and_keeps_delete_payload_none() -> None:
    http = _AsyncCaptureHttpClient()
    client = AsyncFeishuClient(
        FeishuConfig(
            auth_mode="tenant",
            access_token="tenant-token",
        ),
        http_client=cast(AsyncJsonHttpClient, http),
    )

    async def run() -> None:
        await client.request_json("DELETE", "/open-apis/task/v2/tasks/task_1")

    asyncio.run(run())

    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == "https://open.feishu.cn/open-apis/task/v2/tasks/task_1"
    assert call["payload"] is None


def test_async_request_json_does_not_refresh_on_reauthorization_permission_error() -> None:
    http = _AsyncPermissionHttpClient()
    client = AsyncFeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(AsyncJsonHttpClient, http),
    )

    async def run() -> None:
        try:
            await client.request_json("POST", "/base/v3/bases", payload={"name": "Denied"})
        except FeishuError as exc:
            assert "99991672" in str(exc)
        else:
            raise AssertionError("expected FeishuError")

    asyncio.run(run())

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/base/v3/bases"]


def test_async_request_json_does_not_refresh_on_http_unauthorized_permission_error() -> None:
    http = _AsyncHTTPPermissionHttpClient()
    client = AsyncFeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(AsyncJsonHttpClient, http),
    )

    async def run() -> None:
        try:
            await client.request_json("POST", "/base/v3/bases", payload={"name": "Denied"})
        except HTTPRequestError as exc:
            assert exc.status_code == 400
            assert "99991672" in str(exc.response_text)
        else:
            raise AssertionError("expected HTTPRequestError")

    asyncio.run(run())

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/base/v3/bases"]


def test_async_request_json_does_not_refresh_on_business_object_token_error() -> None:
    http = _AsyncBusinessTokenHttpClient()
    client = AsyncFeishuClient(
        FeishuConfig(
            app_id="cli_app",
            app_secret="cli_secret",
            auth_mode="user",
            user_access_token="access-token",
            user_refresh_token="refresh-token",
        ),
        http_client=cast(AsyncJsonHttpClient, http),
    )

    async def run() -> None:
        try:
            await client.request_json("GET", "/docs/v1/content", params={"doc_token": "missing_doc"})
        except FeishuError as exc:
            assert "invalid docs token" in str(exc)
        else:
            raise AssertionError("expected FeishuError")

    asyncio.run(run())

    assert [call["url"].split("/open-apis")[-1] for call in http.calls] == ["/docs/v1/content"]
