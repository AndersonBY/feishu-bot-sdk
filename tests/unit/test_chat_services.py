import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.chat import AsyncChatService, ChatService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient


class _SyncClientStub:
    def __init__(self, resolver: Any) -> None:
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
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


class _AsyncClientStub:
    def __init__(self, resolver: Any) -> None:
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
        call = {
            "method": method,
            "path": path,
            "payload": dict(payload or {}),
            "params": dict(params or {}),
        }
        self.calls.append(call)
        return self._resolver(call)


def test_chat_core_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = ChatService(cast(FeishuClient, stub))

    service.create_chat(
        {"name": "Ops", "owner_id": "ou_1"},
        user_id_type="open_id",
        set_bot_manager=True,
        uuid="uuid_1",
    )
    service.get_chat("oc_1", user_id_type="open_id")
    service.list_chats(user_id_type="open_id", sort_type="ByCreateTimeAsc", page_size=20, page_token="p_1")
    service.search_chats("ops", user_id_type="open_id", page_size=10, page_token="p_2")
    service.get_share_link("oc_1", validity_period="year")
    service.update_chat("oc_1", {"name": "Ops 2"}, user_id_type="open_id")
    service.delete_chat("oc_1")

    assert len(stub.calls) == 7
    assert stub.calls[0]["method"] == "POST"
    assert stub.calls[0]["path"] == "/im/v1/chats"
    assert stub.calls[0]["params"] == {
        "user_id_type": "open_id",
        "set_bot_manager": True,
        "uuid": "uuid_1",
    }
    assert stub.calls[0]["payload"] == {"name": "Ops", "owner_id": "ou_1"}
    assert stub.calls[1]["path"] == "/im/v1/chats/oc_1"
    assert stub.calls[1]["params"] == {"user_id_type": "open_id"}
    assert stub.calls[2]["path"] == "/im/v1/chats"
    assert stub.calls[2]["params"] == {
        "user_id_type": "open_id",
        "sort_type": "ByCreateTimeAsc",
        "page_size": 20,
        "page_token": "p_1",
    }
    assert stub.calls[3]["path"] == "/im/v1/chats/search"
    assert stub.calls[3]["params"] == {
        "user_id_type": "open_id",
        "query": "ops",
        "page_size": 10,
        "page_token": "p_2",
    }
    assert stub.calls[4]["path"] == "/im/v1/chats/oc_1/link"
    assert stub.calls[4]["payload"] == {"validity_period": "year"}
    assert stub.calls[5]["path"] == "/im/v1/chats/oc_1"
    assert stub.calls[5]["params"] == {"user_id_type": "open_id"}
    assert stub.calls[5]["payload"] == {"name": "Ops 2"}
    assert stub.calls[6]["method"] == "DELETE"
    assert stub.calls[6]["path"] == "/im/v1/chats/oc_1"


def test_chat_member_tab_menu_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = ChatService(cast(FeishuClient, stub))

    service.add_managers("oc_1", ["ou_mgr"], member_id_type="open_id")
    service.remove_managers("oc_1", ["cli_app_1"], member_id_type="app_id")
    service.add_members("oc_1", ["ou_1", "ou_2"], member_id_type="open_id", succeed_type=1)
    service.remove_members("oc_1", ["ou_3"], member_id_type="open_id")
    service.join_chat("oc_1")
    service.list_members("oc_1", member_id_type="user_id", page_size=50, page_token="m_1")
    service.check_in_chat("oc_1")
    service.put_top_notice("oc_1", {"chat_top_notice": [{"action_type": "1", "message_id": "om_1"}]})
    service.delete_top_notice("oc_1")
    service.create_tabs("oc_1", [{"tab_name": "Docs"}])
    service.update_tabs("oc_1", [{"tab_id": "tab_1", "tab_name": "Docs"}])
    service.sort_tabs("oc_1", ["tab_msg", "tab_1"])
    service.list_tabs("oc_1")
    service.delete_tabs("oc_1", ["tab_1"])
    service.create_menu("oc_1", {"chat_menu_top_levels": [{"chat_menu_item": {"name": "Docs"}}]})
    service.get_menu("oc_1")
    service.update_menu_item("oc_1", "menu_1", {"update_fields": ["NAME"], "chat_menu_item": {"name": "Docs"}})
    service.sort_menu("oc_1", ["top_1", "top_2"])
    service.delete_menu("oc_1", ["top_2"])

    assert stub.calls[0]["path"] == "/im/v1/chats/oc_1/managers/add_managers"
    assert stub.calls[0]["params"] == {"member_id_type": "open_id"}
    assert stub.calls[0]["payload"] == {"manager_ids": ["ou_mgr"]}
    assert stub.calls[1]["path"] == "/im/v1/chats/oc_1/managers/delete_managers"
    assert stub.calls[1]["params"] == {"member_id_type": "app_id"}
    assert stub.calls[1]["payload"] == {"manager_ids": ["cli_app_1"]}
    assert stub.calls[2]["path"] == "/im/v1/chats/oc_1/members"
    assert stub.calls[2]["params"] == {"member_id_type": "open_id", "succeed_type": 1}
    assert stub.calls[2]["payload"] == {"id_list": ["ou_1", "ou_2"]}
    assert stub.calls[3]["method"] == "DELETE"
    assert stub.calls[3]["payload"] == {"id_list": ["ou_3"]}
    assert stub.calls[4]["path"] == "/im/v1/chats/oc_1/members/me_join"
    assert stub.calls[5]["path"] == "/im/v1/chats/oc_1/members"
    assert stub.calls[5]["params"] == {"member_id_type": "user_id", "page_size": 50, "page_token": "m_1"}
    assert stub.calls[6]["path"] == "/im/v1/chats/oc_1/members/is_in_chat"
    assert stub.calls[7]["path"] == "/im/v1/chats/oc_1/top_notice/put_top_notice"
    assert stub.calls[8]["path"] == "/im/v1/chats/oc_1/top_notice/delete_top_notice"
    assert stub.calls[9]["path"] == "/im/v1/chats/oc_1/chat_tabs"
    assert stub.calls[9]["payload"] == {"chat_tabs": [{"tab_name": "Docs"}]}
    assert stub.calls[10]["path"] == "/im/v1/chats/oc_1/chat_tabs/update_tabs"
    assert stub.calls[11]["payload"] == {"tab_ids": ["tab_msg", "tab_1"]}
    assert stub.calls[12]["path"] == "/im/v1/chats/oc_1/chat_tabs/list_tabs"
    assert stub.calls[13]["method"] == "DELETE"
    assert stub.calls[13]["payload"] == {"tab_ids": ["tab_1"]}
    assert stub.calls[14]["path"] == "/im/v1/chats/oc_1/menu_tree"
    assert stub.calls[14]["payload"] == {
        "menu_tree": {"chat_menu_top_levels": [{"chat_menu_item": {"name": "Docs"}}]}
    }
    assert stub.calls[15]["path"] == "/im/v1/chats/oc_1/menu_tree"
    assert stub.calls[16]["path"] == "/im/v1/chats/oc_1/menu_items/menu_1"
    assert stub.calls[17]["payload"] == {"chat_menu_top_level_ids": ["top_1", "top_2"]}
    assert stub.calls[18]["method"] == "DELETE"
    assert stub.calls[18]["payload"] == {"chat_menu_top_level_ids": ["top_2"]}


def test_chat_announcement_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = ChatService(cast(FeishuClient, stub))

    service.get_announcement("oc_1", user_id_type="open_id")
    service.list_announcement_blocks(
        "oc_1",
        revision_id=2,
        user_id_type="open_id",
        page_size=100,
        page_token="b_1",
    )
    service.get_announcement_block("oc_1", "blk_1", revision_id=2, user_id_type="open_id")
    service.list_announcement_children(
        "oc_1",
        "blk_1",
        revision_id=2,
        user_id_type="open_id",
        page_size=100,
        page_token="c_1",
    )
    service.create_announcement_children(
        "oc_1",
        "blk_1",
        [{"block_type": 2}],
        revision_id=2,
        client_token="token_1",
        user_id_type="open_id",
    )
    service.batch_update_announcement_blocks(
        "oc_1",
        {"requests": [{"update_text_elements": {"block_id": "blk_1", "elements": []}}]},
        revision_id=2,
        client_token="token_2",
        user_id_type="open_id",
    )
    service.delete_announcement_children(
        "oc_1",
        "blk_1",
        {"start_index": 0, "end_index": 1},
        revision_id=2,
        client_token="token_3",
    )

    assert stub.calls[0]["path"] == "/docx/v1/chats/oc_1/announcement"
    assert stub.calls[0]["params"] == {"user_id_type": "open_id"}
    assert stub.calls[1]["path"] == "/docx/v1/chats/oc_1/announcement/blocks"
    assert stub.calls[1]["params"] == {
        "revision_id": 2,
        "user_id_type": "open_id",
        "page_size": 100,
        "page_token": "b_1",
    }
    assert stub.calls[2]["path"] == "/docx/v1/chats/oc_1/announcement/blocks/blk_1"
    assert stub.calls[3]["path"] == "/docx/v1/chats/oc_1/announcement/blocks/blk_1/children"
    assert stub.calls[3]["params"] == {
        "revision_id": 2,
        "user_id_type": "open_id",
        "page_size": 100,
        "page_token": "c_1",
    }
    assert stub.calls[4]["path"] == "/docx/v1/chats/oc_1/announcement/blocks/blk_1/children"
    assert stub.calls[4]["params"] == {
        "revision_id": 2,
        "client_token": "token_1",
        "user_id_type": "open_id",
    }
    assert stub.calls[4]["payload"] == {"children": [{"block_type": 2}]}
    assert stub.calls[5]["path"] == "/docx/v1/chats/oc_1/announcement/blocks/batch_update"
    assert stub.calls[5]["params"] == {
        "revision_id": 2,
        "client_token": "token_2",
        "user_id_type": "open_id",
    }
    assert stub.calls[6]["method"] == "DELETE"
    assert stub.calls[6]["path"] == "/docx/v1/chats/oc_1/announcement/blocks/blk_1/children/batch_delete"
    assert stub.calls[6]["params"] == {"revision_id": 2, "client_token": "token_3"}
    assert stub.calls[6]["payload"] == {"start_index": 0, "end_index": 1}


def test_async_chat_iterators() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        path = str(call["path"])
        params = call["params"]
        page_token = params.get("page_token")
        if path == "/im/v1/chats":
            if page_token == "chat_2":
                return {"code": 0, "data": {"items": [{"chat_id": "oc_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"chat_id": "oc_1"}], "has_more": True, "page_token": "chat_2"}}
        if path == "/im/v1/chats/search":
            if page_token == "search_2":
                return {"code": 0, "data": {"items": [{"chat_id": "oc_4"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"chat_id": "oc_3"}], "has_more": True, "page_token": "search_2"}}
        if path == "/im/v1/chats/oc_1/members":
            if page_token == "member_2":
                return {"code": 0, "data": {"items": [{"member_id": "ou_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"member_id": "ou_1"}], "has_more": True, "page_token": "member_2"}}
        if path == "/im/v1/chats/oc_1/moderation":
            if page_token == "mod_2":
                return {"code": 0, "data": {"items": [{"open_id": "ou_mod_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"open_id": "ou_mod_1"}], "has_more": True, "page_token": "mod_2"}}
        if path == "/docx/v1/chats/oc_1/announcement/blocks":
            if page_token == "block_2":
                return {"code": 0, "data": {"items": [{"block_id": "blk_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"block_id": "blk_1"}], "has_more": True, "page_token": "block_2"}}
        if path == "/docx/v1/chats/oc_1/announcement/blocks/blk_root/children":
            if page_token == "child_2":
                return {"code": 0, "data": {"items": [{"block_id": "child_2"}], "has_more": False}}
            return {"code": 0, "data": {"items": [{"block_id": "child_1"}], "has_more": True, "page_token": "child_2"}}
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    service = AsyncChatService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        chats = [item async for item in service.iter_chats(user_id_type="open_id", page_size=1)]
        search = [item async for item in service.iter_search_chats("ops", user_id_type="open_id", page_size=1)]
        members = [item async for item in service.iter_members("oc_1", member_id_type="open_id", page_size=1)]
        moderation = [item async for item in service.iter_moderation("oc_1", user_id_type="open_id", page_size=1)]
        blocks = [
            item
            async for item in service.iter_announcement_blocks(
                "oc_1",
                revision_id=2,
                user_id_type="open_id",
                page_size=1,
            )
        ]
        children = [
            item
            async for item in service.iter_announcement_children(
                "oc_1",
                "blk_root",
                revision_id=2,
                user_id_type="open_id",
                page_size=1,
            )
        ]

        assert chats == [{"chat_id": "oc_1"}, {"chat_id": "oc_2"}]
        assert search == [{"chat_id": "oc_3"}, {"chat_id": "oc_4"}]
        assert members == [{"member_id": "ou_1"}, {"member_id": "ou_2"}]
        assert moderation == [{"open_id": "ou_mod_1"}, {"open_id": "ou_mod_2"}]
        assert blocks == [{"block_id": "blk_1"}, {"block_id": "blk_2"}]
        assert children == [{"block_id": "child_1"}, {"block_id": "child_2"}]

    asyncio.run(run())
