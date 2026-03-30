from typing import Any

from feishu_bot_sdk.config import FeishuConfig
from feishu_bot_sdk.exceptions import FeishuError
from feishu_bot_sdk.feishu import FeishuClient, _initial_user_token_cache


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
        http_client=http,
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
