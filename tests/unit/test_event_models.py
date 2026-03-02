import asyncio

from feishu_bot_sdk import FeishuEventRegistry, build_event_context
from feishu_bot_sdk.events import (
    CalendarMessageContent,
    FileMessageContent,
    ImageMessageContent,
    MergeForwardMessageContent,
    PostMessageContent,
    P2ApplicationBotMenuV6,
    P2DriveFileBitableFieldChangedV1,
    P2DriveFileBitableRecordChangedV1,
    P2ImMessageReactionCreatedV1,
    P2ImMessageReactionDeletedV1,
    P2ImMessageReadV1,
    P2ImMessageRecalledV1,
    P2ImMessageReceiveV1,
    TextMessageContent,
    UnknownMessageContent,
    parse_received_message_content,
)


def test_bitable_record_changed_model_from_context():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_record_1",
            "event_type": "drive.file.bitable_record_changed_v1",
            "create_time": "1717040601000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "file_type": "bitable",
            "file_token": "base_1",
            "table_id": "tbl_1",
            "revision": "41",
            "operator_id": {
                "union_id": "on_1",
                "user_id": "ouser_1",
                "open_id": "ou_1",
            },
            "action_list": [
                {
                    "record_id": "rec_1",
                    "action": "record_edited",
                }
            ],
            "subscriber_id_list": [
                {
                    "union_id": "on_sub",
                    "user_id": "ouser_sub",
                    "open_id": "ou_sub",
                }
            ],
            "update_time": 1717040601,
        },
    }
    context = build_event_context(payload)

    model = P2DriveFileBitableRecordChangedV1.from_context(context)

    assert model.event_id == "evt_record_1"
    assert model.file_token == "base_1"
    assert model.table_id == "tbl_1"
    assert model.revision == 41
    assert model.operator_open_id == "ou_1"
    assert len(model.action_list) == 1
    assert model.action_list[0]["record_id"] == "rec_1"
    assert len(model.subscriber_id_list) == 1
    assert model.update_time == 1717040601


def test_bitable_field_changed_model_from_context():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_field_1",
            "event_type": "drive.file.bitable_field_changed_v1",
            "create_time": "1717040602000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "file_type": "bitable",
            "file_token": "base_1",
            "table_id": "tbl_1",
            "revision": 10,
            "operator_id": {
                "union_id": "on_2",
                "user_id": "ouser_2",
                "open_id": "ou_2",
            },
            "action_list": [
                {
                    "action": "field_edited",
                    "field_id": "fld_1",
                }
            ],
            "subscriber_id_list": [],
            "update_time": "1717040602",
        },
    }
    context = build_event_context(payload)

    model = P2DriveFileBitableFieldChangedV1.from_context(context)

    assert model.event_id == "evt_field_1"
    assert model.file_token == "base_1"
    assert model.table_id == "tbl_1"
    assert model.revision == 10
    assert model.operator_user_id == "ouser_2"
    assert len(model.action_list) == 1
    assert model.action_list[0]["field_id"] == "fld_1"
    assert model.subscriber_id_list == []
    assert model.update_time == 1717040602


def test_registry_dispatches_bitable_events_with_typed_models():
    captured: list[str] = []
    registry = FeishuEventRegistry()
    registry.on_bitable_record_changed(lambda event: captured.append(f"record:{event.table_id}"))
    registry.on_bitable_field_changed(lambda event: captured.append(f"field:{event.table_id}"))

    registry.dispatch(
        build_event_context(
            {
                "schema": "2.0",
                "header": {
                    "event_id": "evt_record_2",
                    "event_type": "drive.file.bitable_record_changed_v1",
                },
                "event": {
                    "table_id": "tbl_record",
                },
            }
        )
    )
    registry.dispatch(
        build_event_context(
            {
                "schema": "2.0",
                "header": {
                    "event_id": "evt_field_2",
                    "event_type": "drive.file.bitable_field_changed_v1",
                },
                "event": {
                    "table_id": "tbl_field",
                },
            }
        )
    )

    assert captured == ["record:tbl_record", "field:tbl_field"]


def test_registry_adispatches_bitable_event():
    async def run() -> None:
        registry = FeishuEventRegistry()

        async def handle(event: P2DriveFileBitableRecordChangedV1) -> str:
            return event.file_token or ""

        registry.on_bitable_record_changed(handle)
        result = await registry.adispatch(
            build_event_context(
                {
                    "schema": "2.0",
                    "header": {
                        "event_id": "evt_record_3",
                        "event_type": "drive.file.bitable_record_changed_v1",
                    },
                    "event": {
                        "file_token": "base_async",
                    },
                }
            )
        )
        assert result == "base_async"

    asyncio.run(run())


def test_im_message_read_model_from_context():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_read_1",
            "event_type": "im.message.message_read_v1",
            "create_time": "1717040605000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "reader": {
                "reader_id": {
                    "open_id": "ou_read_1",
                    "user_id": "u_read_1",
                    "union_id": "on_read_1",
                },
                "read_time": "1717040605888",
                "tenant_key": "tenant_reader_1",
            },
            "message_id_list": ["om_1", "om_2"],
        },
    }

    model = P2ImMessageReadV1.from_context(build_event_context(payload))

    assert model.event_id == "evt_read_1"
    assert model.reader_open_id == "ou_read_1"
    assert model.reader_user_id == "u_read_1"
    assert model.reader_union_id == "on_read_1"
    assert model.read_time == "1717040605888"
    assert model.reader_tenant_key == "tenant_reader_1"
    assert model.message_id_list == ["om_1", "om_2"]


def test_im_message_recalled_model_from_context():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_recall_1",
            "event_type": "im.message.recalled_v1",
            "create_time": "1717040606000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "message_id": "om_1",
            "chat_id": "oc_1",
            "recall_time": "1717040606666",
            "recall_type": "message_owner",
        },
    }

    model = P2ImMessageRecalledV1.from_context(build_event_context(payload))

    assert model.event_id == "evt_recall_1"
    assert model.message_id == "om_1"
    assert model.chat_id == "oc_1"
    assert model.recall_time == "1717040606666"
    assert model.recall_type == "message_owner"


def test_im_message_reaction_models_from_context():
    created_payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_react_created_1",
            "event_type": "im.message.reaction.created_v1",
            "create_time": "1717040607000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "message_id": "om_1",
            "reaction_type": {"emoji_type": "SMILE"},
            "operator_type": "user",
            "user_id": {"open_id": "ou_1", "user_id": "u_1", "union_id": "on_1"},
            "app_id": "cli_op_1",
            "action_time": "1717040607888",
        },
    }
    deleted_payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_react_deleted_1",
            "event_type": "im.message.reaction.deleted_v1",
            "create_time": "1717040608000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "message_id": "om_2",
            "reaction_type": {"emoji_type": "THUMBSUP"},
            "operator_type": "app",
            "app_id": "cli_op_2",
            "action_time": "1717040608999",
        },
    }

    created = P2ImMessageReactionCreatedV1.from_context(build_event_context(created_payload))
    deleted = P2ImMessageReactionDeletedV1.from_context(build_event_context(deleted_payload))

    assert created.message_id == "om_1"
    assert created.emoji_type == "SMILE"
    assert created.operator_type == "user"
    assert created.operator_open_id == "ou_1"
    assert created.operator_user_id == "u_1"
    assert created.operator_union_id == "on_1"
    assert created.operator_app_id == "cli_op_1"
    assert created.action_time == "1717040607888"

    assert deleted.message_id == "om_2"
    assert deleted.emoji_type == "THUMBSUP"
    assert deleted.operator_type == "app"
    assert deleted.operator_open_id is None
    assert deleted.operator_app_id == "cli_op_2"
    assert deleted.action_time == "1717040608999"


def test_registry_dispatches_additional_im_events_with_typed_models():
    captured: list[str] = []
    registry = FeishuEventRegistry()
    registry.on_im_message_read(lambda event: captured.append(f"read:{event.reader_open_id}"))
    registry.on_im_message_recalled(lambda event: captured.append(f"recalled:{event.message_id}"))
    registry.on_im_message_reaction_created(lambda event: captured.append(f"created:{event.emoji_type}"))
    registry.on_im_message_reaction_deleted(lambda event: captured.append(f"deleted:{event.emoji_type}"))

    registry.dispatch(
        build_event_context(
            {
                "schema": "2.0",
                "header": {"event_id": "evt_1", "event_type": "im.message.message_read_v1"},
                "event": {"reader": {"reader_id": {"open_id": "ou_read"}}},
            }
        )
    )
    registry.dispatch(
        build_event_context(
            {
                "schema": "2.0",
                "header": {"event_id": "evt_2", "event_type": "im.message.recalled_v1"},
                "event": {"message_id": "om_recalled"},
            }
        )
    )
    registry.dispatch(
        build_event_context(
            {
                "schema": "2.0",
                "header": {"event_id": "evt_3", "event_type": "im.message.reaction.created_v1"},
                "event": {"reaction_type": {"emoji_type": "SMILE"}},
            }
        )
    )
    registry.dispatch(
        build_event_context(
            {
                "schema": "2.0",
                "header": {"event_id": "evt_4", "event_type": "im.message.reaction.deleted_v1"},
                "event": {"reaction_type": {"emoji_type": "THUMBSUP"}},
            }
        )
    )

    assert captured == [
        "read:ou_read",
        "recalled:om_recalled",
        "created:SMILE",
        "deleted:THUMBSUP",
    ]


def test_bot_menu_model_reads_operator_ids_from_operator_id():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_menu_1",
            "event_type": "application.bot.menu_v6",
            "create_time": "1717040603000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "operator": {
                "operator_id": {
                    "open_id": "ou_menu_1",
                    "user_id": "ouser_menu_1",
                    "union_id": "on_menu_1",
                }
            },
            "event_key": "help",
        },
    }
    context = build_event_context(payload)

    model = P2ApplicationBotMenuV6.from_context(context)

    assert model.event_id == "evt_menu_1"
    assert model.event_key == "help"
    assert model.operator_open_id == "ou_menu_1"
    assert model.operator_user_id == "ouser_menu_1"
    assert model.operator_union_id == "on_menu_1"


def test_bot_menu_model_prefers_direct_operator_ids_when_present():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_menu_2",
            "event_type": "application.bot.menu_v6",
        },
        "event": {
            "operator": {
                "open_id": "ou_direct",
                "user_id": "ouser_direct",
                "union_id": "on_direct",
                "operator_id": {
                    "open_id": "ou_nested",
                    "user_id": "ouser_nested",
                    "union_id": "on_nested",
                },
            },
            "event_key": "menu-key",
        },
    }
    context = build_event_context(payload)

    model = P2ApplicationBotMenuV6.from_context(context)

    assert model.operator_open_id == "ou_direct"
    assert model.operator_user_id == "ouser_direct"
    assert model.operator_union_id == "on_direct"


def test_parse_received_message_content_for_common_types():
    text = parse_received_message_content(
        message_type="text",
        content_raw='{"text":"hello"}',
    )
    assert isinstance(text, TextMessageContent)
    assert text.text == "hello"

    image = parse_received_message_content(
        message_type="image",
        content_raw='{"image_key":"img_1"}',
    )
    assert isinstance(image, ImageMessageContent)
    assert image.image_key == "img_1"

    file_content = parse_received_message_content(
        message_type="file",
        content_raw='{"file_key":"file_1","file_name":"demo.txt"}',
    )
    assert isinstance(file_content, FileMessageContent)
    assert file_content.file_key == "file_1"
    assert file_content.file_name == "demo.txt"

    post = parse_received_message_content(
        message_type="post",
        content_raw='{"title":"日报","content":[[{"tag":"text","text":"hello"}]]}',
    )
    assert isinstance(post, PostMessageContent)
    assert post.title == "日报"
    assert post.content[0][0]["tag"] == "text"

    calendar = parse_received_message_content(
        message_type="calendar",
        content_raw='{"summary":"会议","start_time":"1","end_time":"2"}',
    )
    assert isinstance(calendar, CalendarMessageContent)
    assert calendar.summary == "会议"
    assert calendar.message_type == "calendar"

    merge_forward = parse_received_message_content(
        message_type="merge_forward",
        content_raw='{"content":"Merged and Forwarded Message"}',
    )
    assert isinstance(merge_forward, MergeForwardMessageContent)
    assert merge_forward.content == "Merged and Forwarded Message"


def test_parse_received_message_content_returns_unknown_for_invalid_payload():
    parsed = parse_received_message_content(
        message_type="text",
        content_raw="{invalid-json",
    )
    assert isinstance(parsed, UnknownMessageContent)
    assert parsed.message_type == "text"
    assert parsed.parse_error is not None

    unknown_type = parse_received_message_content(
        message_type="new_type",
        content_raw='{"k":"v"}',
    )
    assert isinstance(unknown_type, UnknownMessageContent)
    assert unknown_type.message_type == "new_type"
    assert unknown_type.raw["k"] == "v"


def test_im_message_receive_model_parses_typed_content():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_msg_1",
            "event_type": "im.message.receive_v1",
            "create_time": "1717040604000",
            "tenant_key": "tenant_1",
            "app_id": "cli_1",
        },
        "event": {
            "message": {
                "message_id": "om_1",
                "chat_id": "oc_1",
                "chat_type": "p2p",
                "message_type": "text",
                "content": '{"text":"hello event"}',
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_1",
                    "user_id": "u_1",
                    "union_id": "on_1",
                }
            },
        },
    }
    model = P2ImMessageReceiveV1.from_context(build_event_context(payload))
    assert isinstance(model.content, TextMessageContent)
    assert model.content.text == "hello event"
    assert model.content_raw == '{"text":"hello event"}'
    assert model.text == "hello event"
