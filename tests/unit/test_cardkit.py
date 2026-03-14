import asyncio
from typing import Any, Mapping, Optional

from feishu_bot_sdk.callbacks import CardCallbackResponse
from feishu_bot_sdk.cardkit import (
    AsyncCardKitService,
    CardKitCreateResponse,
    CardKitResponse,
    CardKitService,
)
from feishu_bot_sdk.events import P2CardActionTrigger, build_event_context


# ---------------------------------------------------------------------------
# Client stubs (same pattern as test_im_services.py)
# ---------------------------------------------------------------------------


class _SyncClientStub:
    def __init__(self, resolver=None):
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        self.calls.append({"method": method, "path": path, "payload": dict(payload or {})})
        if self._resolver:
            return self._resolver(self.calls[-1])
        return {"code": 0, "data": {}}


class _AsyncClientStub:
    def __init__(self, resolver=None):
        self._resolver = resolver
        self.calls: list[dict[str, Any]] = []

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        payload: Optional[Mapping[str, object]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        self.calls.append({"method": method, "path": path, "payload": dict(payload or {})})
        if self._resolver:
            return self._resolver(self.calls[-1])
        return {"code": 0, "data": {}}


# ---------------------------------------------------------------------------
# CardKitResponse tests
# ---------------------------------------------------------------------------


def test_cardkit_response_from_raw_ok():
    resp = CardKitResponse.from_raw({"code": 0, "msg": "success"})
    assert resp.ok
    assert resp.code == 0
    assert resp.msg == "success"


def test_cardkit_response_from_raw_error():
    resp = CardKitResponse.from_raw({"code": 230001, "msg": "invalid card"})
    assert not resp.ok
    assert resp.code == 230001


def test_cardkit_create_response_extracts_card_id():
    resp = CardKitCreateResponse.from_raw({
        "code": 0,
        "msg": "success",
        "data": {"card_id": "ck_abc123"},
    })
    assert resp.ok
    assert resp.card_id == "ck_abc123"


def test_cardkit_create_response_fallback_card_id():
    resp = CardKitCreateResponse.from_raw({
        "code": 0,
        "msg": "",
        "card_id": "ck_fallback",
    })
    assert resp.card_id == "ck_fallback"


# ---------------------------------------------------------------------------
# CardKitService sync tests
# ---------------------------------------------------------------------------


def _create_resolver(call):
    return {"code": 0, "data": {"card_id": "ck_new"}, "msg": ""}


def test_cardkit_service_create():
    stub = _SyncClientStub(resolver=_create_resolver)
    svc = CardKitService(stub)  # type: ignore[arg-type]
    resp = svc.create(card={"elements": []})
    assert resp.ok
    assert resp.card_id == "ck_new"
    assert stub.calls[0]["method"] == "POST"
    assert "/cardkit/v1/cards" in stub.calls[0]["path"]


def test_cardkit_service_update():
    stub = _SyncClientStub()
    svc = CardKitService(stub)  # type: ignore[arg-type]
    resp = svc.update("ck_1", card={"elements": []}, sequence=5)
    assert resp.ok
    assert stub.calls[0]["method"] == "PUT"
    assert "ck_1" in stub.calls[0]["path"]
    assert stub.calls[0]["payload"]["sequence"] == 5


def test_cardkit_service_set_element_content():
    stub = _SyncClientStub()
    svc = CardKitService(stub)  # type: ignore[arg-type]
    resp = svc.set_element_content("ck_1", element_id="el_1", content="hello", sequence=2)
    assert resp.ok
    assert "el_1" in stub.calls[0]["path"]
    assert stub.calls[0]["payload"]["content"] == "hello"


def test_cardkit_service_set_streaming_mode():
    stub = _SyncClientStub()
    svc = CardKitService(stub)  # type: ignore[arg-type]
    resp = svc.set_streaming_mode("ck_1", enabled=True, sequence=1)
    assert resp.ok
    assert "settings" in stub.calls[0]["path"]


# ---------------------------------------------------------------------------
# AsyncCardKitService tests
# ---------------------------------------------------------------------------


def test_async_cardkit_service_create():
    stub = _AsyncClientStub(resolver=_create_resolver)
    svc = AsyncCardKitService(stub)  # type: ignore[arg-type]
    resp = asyncio.get_event_loop().run_until_complete(svc.create(card={"elements": []}))
    assert resp.ok
    assert resp.card_id == "ck_new"


def test_async_cardkit_service_set_element_content():
    stub = _AsyncClientStub()
    svc = AsyncCardKitService(stub)  # type: ignore[arg-type]
    resp = asyncio.get_event_loop().run_until_complete(
        svc.set_element_content("ck_1", element_id="el_1", content="world", sequence=3)
    )
    assert resp.ok


# ---------------------------------------------------------------------------
# P2CardActionTrigger expanded fields
# ---------------------------------------------------------------------------


def test_card_action_trigger_expanded_fields():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_card_1",
            "event_type": "card.action.trigger",
            "create_time": "1717040601000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
            "token": "verify_token_abc",
        },
        "event": {
            "operator": {
                "open_id": "ou_operator",
                "user_id": "uid_operator",
                "union_id": "on_operator",
            },
            "action": {
                "tag": "button",
                "value": {"action": "confirm", "id": "42"},
            },
            "context": {
                "open_message_id": "om_msg_1",
                "open_chat_id": "oc_chat_1",
            },
            "action_time": "1717040602000",
        },
    }
    context = build_event_context(payload, is_callback=True)
    trigger = P2CardActionTrigger.from_context(context)

    assert trigger.event_id == "evt_card_1"
    assert trigger.tenant_key == "tenant_1"
    assert trigger.app_id == "cli_1"
    assert trigger.open_id == "ou_operator"
    assert trigger.user_id == "uid_operator"
    assert trigger.union_id == "on_operator"
    assert trigger.action_tag == "button"
    assert trigger.action_value == {"action": "confirm", "id": "42"}
    assert trigger.open_message_id == "om_msg_1"
    assert trigger.open_chat_id == "oc_chat_1"
    assert trigger.trigger_time == "1717040602000"
    assert trigger.token == "verify_token_abc"
    # raw action/operator dicts preserved
    assert trigger.action["tag"] == "button"
    assert trigger.operator["union_id"] == "on_operator"


def test_card_action_trigger_fallback_fields():
    """When context sub-object is missing, fields fall back gracefully."""
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_2",
            "event_type": "card.action.trigger",
            "create_time": "1717040601000",
            "tenant_key": "t",
            "app_id": "a",
        },
        "event": {
            "operator": {"open_id": "ou_1"},
            "action": {"tag": "select", "value": {}},
            "open_message_id": "om_direct",
            "open_chat_id": "oc_direct",
        },
    }
    context = build_event_context(payload, is_callback=True)
    trigger = P2CardActionTrigger.from_context(context)
    assert trigger.open_message_id == "om_direct"
    assert trigger.open_chat_id == "oc_direct"
    assert trigger.trigger_time == "1717040601000"  # falls back to create_time
    assert trigger.union_id is None


# ---------------------------------------------------------------------------
# CardCallbackResponse tests
# ---------------------------------------------------------------------------


def test_callback_toast():
    result = CardCallbackResponse.toast("Done!", type="success")
    assert result == {"toast": {"type": "success", "content": "Done!"}}


def test_callback_toast_with_i18n():
    result = CardCallbackResponse.toast("OK", i18n={"en_us": "OK", "zh_cn": "好的"})
    assert result["toast"]["i18n"]["zh_cn"] == "好的"


def test_callback_card_raw():
    card = {"elements": [{"tag": "div"}]}
    result = CardCallbackResponse.card(card)
    assert result == {"card": {"elements": [{"tag": "div"}]}}


def test_callback_card_typed():
    result = CardCallbackResponse.card({"template_id": "tpl_1"}, card_type="template")
    assert result["card"]["type"] == "template"


def test_callback_inline():
    result = CardCallbackResponse.inline(toast={"type": "info"}, custom="value")
    assert result["toast"] == {"type": "info"}
    assert result["custom"] == "value"
