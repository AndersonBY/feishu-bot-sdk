import argparse
import io
import json
from pathlib import Path
from typing import Any
from feishu_bot_sdk import cli
from feishu_bot_sdk.bot import BotService
from feishu_bot_sdk.config import FeishuConfig
from feishu_bot_sdk.exceptions import FeishuError, HTTPRequestError
from feishu_bot_sdk.feishu import OAuthUserToken
from feishu_bot_sdk.token_store import StoredUserToken


def _base_args(**overrides: Any) -> argparse.Namespace:
    data: dict[str, Any] = {
        "app_id": None,
        "app_secret": None,
        "auth_mode": None,
        "access_token": None,
        "app_access_token": None,
        "user_access_token": None,
        "user_refresh_token": None,
        "base_url": None,
        "timeout": None,
    }
    data.update(overrides)
    return argparse.Namespace(**data)


def test_build_config_prefers_env_credentials(monkeypatch: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "env_app_id")
    monkeypatch.setenv("FEISHU_APP_SECRET", "env_app_secret")

    config = cli._build_config(
        _base_args(app_id="arg_app_id", app_secret="arg_app_secret")
    )

    assert isinstance(config, FeishuConfig)
    assert config.app_id == "env_app_id"
    assert config.app_secret == "env_app_secret"


def test_build_config_accepts_auto_mode_with_user_token() -> None:
    config = cli._build_config(
        _base_args(
            auth_mode="auto",
            app_id="cli_app",
            app_secret="cli_secret",
            user_access_token="user_token_1",
        )
    )

    assert config.auth_mode == "auto"
    assert config.user_access_token == "user_token_1"


def test_build_config_uses_user_token_from_store_when_env_and_args_missing() -> None:
    store_token = StoredUserToken(
        access_token="store_access_token",
        expires_at=123456.0,
    )
    context = cli._UserTokenStoreContext(
        enabled=True,
        profile="default",
        store_path=Path("tokens.json"),
        store=None,
        from_env_or_arg=False,
        loaded_token=store_token,
    )
    config = cli._build_config(
        _base_args(auth_mode="user"), force_user_auth=True, token_context=context
    )
    assert config.access_token is None
    assert config.user_access_token == "store_access_token"
    assert config.user_refresh_token is None
    assert config.user_access_token_expires_at == 123456.0
    assert config.user_refresh_token_expires_at is None


def test_build_config_prefers_env_user_token_over_store(monkeypatch: Any) -> None:
    monkeypatch.setenv("FEISHU_USER_ACCESS_TOKEN", "env_user_access_token")
    store_token = StoredUserToken(
        access_token="store_access_token",
        expires_at=123456.0,
    )
    context = cli._UserTokenStoreContext(
        enabled=True,
        profile="default",
        store_path=Path("tokens.json"),
        store=None,
        from_env_or_arg=True,
        loaded_token=store_token,
    )
    config = cli._build_config(
        _base_args(auth_mode="user"), force_user_auth=True, token_context=context
    )
    assert config.access_token is None
    assert config.user_access_token == "env_user_access_token"
    assert config.user_access_token_expires_at is None


def test_auth_token_json_output(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.get_access_token",
        lambda _self: "t-env",
    )

    code = cli.main(["auth", "token", "--format", "json"])
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["access_token"] == "t-env"


def test_auth_request_payload_from_stdin(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")
    monkeypatch.setattr("sys.stdin", io.StringIO('{"x": 1}'))

    captured: dict[str, Any] = {}

    def _fake_request_json(
        _self: Any,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        captured["method"] = method
        captured["path"] = path
        captured["payload"] = payload
        captured["params"] = params
        return {"code": 0, "echo": payload}

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.request_json", _fake_request_json
    )

    code = cli.main(
        ["auth", "request", "POST", "/x/y", "--payload-stdin", "--format", "json"]
    )
    assert code == 0
    assert captured["method"] == "POST"
    assert captured["path"] == "/x/y"
    assert captured["payload"] == {"x": 1}
    payload = json.loads(capsys.readouterr().out)
    assert payload["echo"] == {"x": 1}


def test_extract_required_user_scopes() -> None:
    text = (
        "required one of these privileges under the user identity: "
        "[contact:user:search, contact:contact.base:readonly, contact:user:search]"
    )
    assert (
        cli._extract_required_user_scopes(text)
        == "contact:user:search contact:contact.base:readonly"
    )


def test_format_http_error_permission_hint_includes_scope_suggestion() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text=(
            '{"code":99991679,"msg":"Unauthorized. required one of these privileges under the user identity: '
            '[contact:user:search, contact:contact.base:readonly]"}'
        ),
    )
    message = cli._format_http_error(exc)
    assert "missing user scopes" in message
    assert "contact:user:search contact:contact.base:readonly" in message


def test_format_http_error_redirect_uri_hint() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text='{"code":20029,"msg":"redirect_uri request is illegal"}',
    )
    message = cli._format_http_error(exc)
    assert "oauth redirect_uri is invalid" in message


def test_format_http_error_invalid_token_hint() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text='{"code":99991668,"msg":"Invalid access token for authorization"}',
    )
    message = cli._format_http_error(exc)
    assert "invalid access token" in message
    assert "feishu auth login --scope" in message


def test_format_http_error_user_access_token_not_supported_hint() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text='{"code":99991668,"msg":"user access token not support"}',
    )
    message = cli._format_http_error(exc)
    assert "does not support user access token" in message
    assert "--auth-mode tenant" in message


def test_format_http_error_invalid_request_param_hint_for_media_resource() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text='{"code":234001,"msg":"Invalid request param."}',
    )
    message = cli._format_http_error(exc)
    assert "invalid request parameters" in message
    assert "--message-id" in message


def test_format_http_error_resource_sender_hint() -> None:
    exc = HTTPRequestError(
        "http request failed",
        status_code=400,
        response_text='{"code":234008,"msg":"The app is not the resource sender."}',
    )
    message = cli._format_http_error(exc)
    assert "message resource download" in message
    assert "--message-id" in message


def test_format_feishu_error_message_token_hints() -> None:
    invalid_access = cli._format_feishu_error_message(
        "feishu api failed: {'code': 20005, 'msg': 'invalid access token'}"
    )
    assert "re-login" in invalid_access

    invalid_refresh = cli._format_feishu_error_message(
        "feishu api failed: {'code': 20026, 'msg': 'refresh token is invalid'}"
    )
    assert "refresh token is invalid" in invalid_refresh
    assert "clear FEISHU_USER_REFRESH_TOKEN" in invalid_refresh


def test_cli_main_feishu_error_uses_hint(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_get_info(_self: BotService) -> Any:
        raise FeishuError(
            "feishu api failed: {'code': 20026, 'msg': 'refresh token is invalid'}"
        )

    monkeypatch.setattr("feishu_bot_sdk.bot.BotService.get_info", _fake_get_info)

    code = cli.main(["bot", "info", "--format", "json"])
    assert code == 3
    payload = json.loads(capsys.readouterr().out)
    assert "refresh token is invalid" in payload["error"]
    assert "clear FEISHU_USER_REFRESH_TOKEN" in payload["error"]


def test_auth_login_stores_user_token(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_wait_for_oauth_callback(
        *, host: str, port: int, path: str, timeout_seconds: float
    ) -> dict[str, str]:
        assert host == "127.0.0.1"
        assert port == 18080
        assert path == "/callback"
        assert timeout_seconds == 180.0
        return {"code": "code_123", "state": "state_123"}

    def _fake_exchange(
        _self: Any,
        code: str,
        *,
        grant_type: str = "authorization_code",
        redirect_uri: str | None = None,
        code_verifier: str | None = None,
    ) -> OAuthUserToken:
        assert code == "code_123"
        assert grant_type == "authorization_code"
        assert redirect_uri == "http://127.0.0.1:18080/callback"
        assert isinstance(code_verifier, str) and code_verifier
        return OAuthUserToken(
            access_token="u_token_1",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="u_refresh_1",
            refresh_expires_in=36000,
            open_id="ou_123",
        )

    monkeypatch.setattr(
        "feishu_bot_sdk.cli._wait_for_oauth_callback", _fake_wait_for_oauth_callback
    )
    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.exchange_authorization_code", _fake_exchange
    )

    store_path = tmp_path / "tokens.json"
    code = cli.main(
        [
            "auth",
            "login",
            "--state",
            "state_123",
            "--no-browser",
            "--token-store",
            str(store_path),
            "--profile",
            "default",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["access_token"] == "u_token_1"
    assert payload["stored"] is True
    stored = json.loads(store_path.read_text(encoding="utf-8"))
    profile = stored["profiles"]["default"]
    assert profile["access_token"] == "u_token_1"
    assert profile["refresh_token"] == "u_refresh_1"
    assert profile["open_id"] == "ou_123"


def test_auth_logout_clears_profile(
    monkeypatch: Any, tmp_path: Path, capsys: Any
) -> None:
    store_path = tmp_path / "tokens.json"
    store_path.write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": {
                    "default": {
                        "access_token": "u_token_1",
                        "refresh_token": "u_refresh_1",
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    code = cli.main(
        [
            "auth",
            "logout",
            "--token-store",
            str(store_path),
            "--profile",
            "default",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["deleted"] is True
    data = json.loads(store_path.read_text(encoding="utf-8"))
    assert data["profiles"] == {}


def test_oauth_authorize_url(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")

    code = cli.main(
        [
            "oauth",
            "authorize-url",
            "--redirect-uri",
            "https://example.com/callback",
            "--state",
            "state-1",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "authen/v1/authorize" in payload["authorize_url"]
    assert "app_id=cli_test_app" in payload["authorize_url"]


def test_oauth_exchange_code(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("FEISHU_APP_ID", "cli_test_app")
    monkeypatch.setenv("FEISHU_APP_SECRET", "cli_test_secret")

    def _fake_exchange(
        _self: Any,
        code: str,
        *,
        grant_type: str = "authorization_code",
        redirect_uri: str | None = None,
        code_verifier: str | None = None,
    ) -> OAuthUserToken:
        assert code == "code_123"
        assert grant_type == "authorization_code"
        assert redirect_uri is None
        assert code_verifier is None
        return OAuthUserToken(
            access_token="u_token_1",
            token_type="Bearer",
            expires_in=7200,
            refresh_token="u_refresh_1",
        )

    monkeypatch.setattr(
        "feishu_bot_sdk.feishu.FeishuClient.exchange_authorization_code", _fake_exchange
    )

    code = cli.main(
        [
            "oauth",
            "exchange-code",
            "--code",
            "code_123",
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["access_token"] == "u_token_1"
