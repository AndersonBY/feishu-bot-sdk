import json

from feishu_bot_sdk import FeishuEventRegistry
from feishu_bot_sdk.ws.constants import MESSAGE_TYPE_CARD, MESSAGE_TYPE_EVENT
from feishu_bot_sdk.ws.dispatcher import WSDispatcher
from feishu_bot_sdk.ws.frames import FrameCombiner, frame_headers_to_dict, new_ping_frame, parse_frame, serialize_frame


def test_ws_dispatcher_routes_message_event():
    captured: list[str] = []
    registry = FeishuEventRegistry()
    registry.on_im_message_receive(lambda event: captured.append(event.text or ""))
    dispatcher = WSDispatcher(registry)

    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_1",
            "event_type": "im.message.receive_v1",
        },
        "event": {
            "message": {
                "message_id": "om_1",
                "message_type": "text",
                "content": "{\"text\":\"hello\"}",
            }
        },
    }
    result = dispatcher.dispatch(json.dumps(payload).encode("utf-8"), message_type=MESSAGE_TYPE_EVENT)
    assert result is None
    assert captured == ["hello"]


def test_ws_dispatcher_routes_card_callback_response():
    registry = FeishuEventRegistry()
    registry.on_card_action_trigger(lambda event: {"toast": {"type": "info", "content": event.action_tag or "ok"}})
    dispatcher = WSDispatcher(registry)

    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_2",
            "event_type": "card.action.trigger",
        },
        "event": {
            "action": {
                "tag": "button",
                "value": {"k": "v"},
            }
        },
    }
    result = dispatcher.dispatch(json.dumps(payload).encode("utf-8"), message_type=MESSAGE_TYPE_CARD)
    assert result == {"toast": {"type": "info", "content": "button"}}


def test_frame_combiner_merges_fragments():
    combiner = FrameCombiner()
    assert combiner.append("msg-1", b"hello ", total=2, seq=0) is None
    merged = combiner.append("msg-1", b"world", total=2, seq=1)
    assert merged == b"hello world"


def test_ping_frame_roundtrip():
    frame = new_ping_frame(123)
    raw = serialize_frame(frame)
    parsed = parse_frame(raw)
    headers = frame_headers_to_dict(parsed)
    assert parsed.service == 123
    assert headers["type"] == "ping"
