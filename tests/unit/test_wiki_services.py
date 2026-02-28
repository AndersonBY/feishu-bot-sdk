import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.docs_content import AsyncDocContentService, DocContentService
from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.wiki import AsyncWikiService, WikiService


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


def test_wiki_space_and_node_requests():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = WikiService(cast(FeishuClient, stub))

    service.create_space({"name": "Team Wiki"})
    service.get_space("space_1", lang="zh")
    service.create_node("space_1", {"obj_type": "docx", "node_type": "origin"})
    service.copy_node("space_1", "wik_1", target_space_id="space_2", title="copy")
    service.move_node("space_1", "wik_1", target_parent_token="wik_parent")
    service.update_node_title("space_1", "wik_1", title="updated")
    service.move_docs_to_wiki("space_1", obj_type="docx", obj_token="doc_1", apply=True)
    service.get_task("task_1", task_type="move")

    assert len(stub.calls) == 8
    assert stub.calls[0]["path"] == "/wiki/v2/spaces"
    assert stub.calls[1]["params"] == {"lang": "zh"}
    assert stub.calls[2]["path"] == "/wiki/v2/spaces/space_1/nodes"
    assert stub.calls[3]["path"] == "/wiki/v2/spaces/space_1/nodes/wik_1/copy"
    assert stub.calls[3]["payload"] == {"target_space_id": "space_2", "title": "copy"}
    assert stub.calls[4]["path"] == "/wiki/v2/spaces/space_1/nodes/wik_1/move"
    assert stub.calls[5]["path"] == "/wiki/v2/spaces/space_1/nodes/wik_1/update_title"
    assert stub.calls[6]["path"] == "/wiki/v2/spaces/space_1/nodes/move_docs_to_wiki"
    assert stub.calls[7]["path"] == "/wiki/v2/tasks/task_1"
    assert stub.calls[7]["params"] == {"task_type": "move"}


def test_wiki_search_and_member_pagination():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"] == "/wiki/v2/nodes/search":
            page_token = call["params"].get("page_token")
            if page_token == "next":
                return {"code": 0, "data": {"items": [{"node_id": "wik_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {
                    "items": [{"node_id": "wik_1"}],
                    "has_more": True,
                    "page_token": "next",
                },
            }
        page_token = call["params"].get("page_token")
        if page_token == "m2":
            return {"code": 0, "data": {"members": [{"member_id": "ou_2"}], "has_more": False}}
        return {
            "code": 0,
            "data": {
                "members": [{"member_id": "ou_1"}],
                "has_more": True,
                "page_token": "m2",
            },
        }

    stub = _SyncClientStub(resolver)
    service = WikiService(cast(FeishuClient, stub))

    search_items = list(service.iter_search_nodes("keyword", page_size=1))
    members = list(service.iter_members("space_1", page_size=1))

    assert search_items == [{"node_id": "wik_1"}, {"node_id": "wik_2"}]
    assert members == [{"member_id": "ou_1"}, {"member_id": "ou_2"}]
    assert stub.calls[0]["path"] == "/wiki/v2/nodes/search"
    assert stub.calls[0]["payload"] == {"query": "keyword"}
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "next"}
    assert stub.calls[2]["path"] == "/wiki/v2/spaces/space_1/members"
    assert stub.calls[3]["params"] == {"page_size": 1, "page_token": "m2"}


def test_wiki_member_management_payloads():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = WikiService(cast(FeishuClient, stub))

    service.add_member(
        "space_1",
        member_type="openid",
        member_id="ou_1",
        member_role="admin",
        collaborator_type="user",
        need_notification=True,
    )
    service.remove_member(
        "space_1",
        "ou_1",
        member_type="openid",
        member_role="admin",
    )
    service.update_space_setting("space_1", {"create_setting": "admin"})

    assert len(stub.calls) == 3
    assert stub.calls[0]["path"] == "/wiki/v2/spaces/space_1/members"
    assert stub.calls[0]["params"] == {"need_notification": True}
    assert stub.calls[0]["payload"] == {
        "member_type": "openid",
        "member_id": "ou_1",
        "member_role": "admin",
        "type": "user",
    }
    assert stub.calls[1]["method"] == "DELETE"
    assert stub.calls[1]["path"] == "/wiki/v2/spaces/space_1/members/ou_1"
    assert stub.calls[1]["payload"] == {
        "member_type": "openid",
        "member_role": "admin",
    }
    assert stub.calls[2]["path"] == "/wiki/v2/spaces/space_1/setting"


def test_doc_content_services():
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"content": "# title"}}

    stub = _SyncClientStub(resolver)
    service = DocContentService(cast(FeishuClient, stub))

    data = service.get_content("doc_1", doc_type="docx", content_type="markdown", lang="en")
    markdown = service.get_markdown("doc_1")

    assert data == {"content": "# title"}
    assert markdown == "# title"
    assert stub.calls[0]["path"] == "/docs/v1/content"
    assert stub.calls[0]["params"] == {
        "doc_token": "doc_1",
        "doc_type": "docx",
        "content_type": "markdown",
        "lang": "en",
    }


def test_async_wiki_and_doc_content_service():
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        if call["path"] == "/wiki/v2/spaces":
            return {"code": 0, "data": {"items": [{"space_id": "space_1"}], "has_more": False}}
        if call["path"] == "/wiki/v2/nodes/search":
            return {"code": 0, "data": {"items": [{"node_id": "wik_1"}], "has_more": False}}
        return {"code": 0, "data": {"content": "async"}}

    stub = _AsyncClientStub(resolver)
    wiki = AsyncWikiService(cast(AsyncFeishuClient, stub))
    docs = AsyncDocContentService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        spaces = []
        async for item in wiki.iter_spaces(page_size=10):
            spaces.append(item)
        search_items = []
        async for item in wiki.iter_search_nodes("wiki", page_size=10):
            search_items.append(item)
        markdown = await docs.get_markdown("doc_1")
        assert spaces == [{"space_id": "space_1"}]
        assert search_items == [{"node_id": "wik_1"}]
        assert markdown == "async"

    asyncio.run(run())
    assert stub.calls[0]["path"] == "/wiki/v2/spaces"
    assert stub.calls[1]["path"] == "/wiki/v2/nodes/search"
    assert stub.calls[2]["path"] == "/docs/v1/content"
