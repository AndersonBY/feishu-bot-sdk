import asyncio

from feishu_bot_sdk import FeishuEventRegistry, build_event_context
from feishu_bot_sdk.events import (
    P2ApplicationBotMenuV6,
    P2DriveFileBitableFieldChangedV1,
    P2DriveFileBitableRecordChangedV1,
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
