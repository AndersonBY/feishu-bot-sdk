import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.feishu import AsyncFeishuClient, FeishuClient
from feishu_bot_sdk.search import AsyncSearchService, SearchService


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


def test_search_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = SearchService(cast(FeishuClient, stub))

    service.search_apps("calendar", user_id_type="open_id", page_size=10, page_token="next_1")
    service.search_messages(
        "incident",
        user_id_type="open_id",
        page_size=5,
        page_token="next_2",
        from_ids=["ou_1", " "],
        chat_ids=["oc_1"],
        message_type="image",
        at_chatter_ids=["ou_2"],
        from_type="user",
        chat_type="group_chat",
        start_time="1700000000",
        end_time="1700003600",
    )
    service.search_doc_wiki(
        "weekly",
        doc_filter={"only_title": True},
        wiki_filter={"space_ids": ["space_1"]},
        page_size=20,
        page_token="next_3",
    )

    assert len(stub.calls) == 3
    assert stub.calls[0]["path"] == "/search/v2/app"
    assert stub.calls[0]["params"] == {"user_id_type": "open_id", "page_size": 10, "page_token": "next_1"}
    assert stub.calls[0]["payload"] == {"query": "calendar"}
    assert stub.calls[1]["path"] == "/search/v2/message"
    assert stub.calls[1]["params"] == {"user_id_type": "open_id", "page_size": 5, "page_token": "next_2"}
    assert stub.calls[1]["payload"] == {
        "query": "incident",
        "from_ids": ["ou_1"],
        "chat_ids": ["oc_1"],
        "message_type": "image",
        "at_chatter_ids": ["ou_2"],
        "from_type": "user",
        "chat_type": "group_chat",
        "start_time": "1700000000",
        "end_time": "1700003600",
    }
    assert stub.calls[2]["path"] == "/search/v2/doc_wiki/search"
    assert stub.calls[2]["payload"] == {
        "query": "weekly",
        "doc_filter": {"only_title": True},
        "wiki_filter": {"space_ids": ["space_1"]},
        "page_token": "next_3",
        "page_size": 20,
    }


def test_async_search_iterators() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        path = str(call["path"])
        params = call["params"]
        payload = call["payload"]
        page_token = params.get("page_token") or payload.get("page_token")
        if path == "/search/v2/app":
            if page_token == "app_2":
                return {"code": 0, "data": {"items": ["cli_2"], "has_more": False}}
            return {"code": 0, "data": {"items": ["cli_1"], "has_more": True, "page_token": "app_2"}}
        if path == "/search/v2/message":
            if page_token == "msg_2":
                return {"code": 0, "data": {"items": ["om_2"], "has_more": False}}
            return {"code": 0, "data": {"items": ["om_1"], "has_more": True, "page_token": "msg_2"}}
        if path == "/search/v2/doc_wiki/search":
            if page_token == "doc_2":
                return {"code": 0, "data": {"res_units": [{"token": "doc_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"res_units": [{"token": "doc_1"}], "has_more": True, "page_token": "doc_2"},
            }
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    service = AsyncSearchService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        apps = [item async for item in service.iter_search_apps("calendar", page_size=1)]
        messages = [item async for item in service.iter_search_messages("incident", page_size=1)]
        docs = [item async for item in service.iter_search_doc_wiki("weekly", page_size=1)]
        assert apps == ["cli_1", "cli_2"]
        assert messages == ["om_1", "om_2"]
        assert docs == [{"token": "doc_1"}, {"token": "doc_2"}]

    asyncio.run(run())

    assert stub.calls[0]["path"] == "/search/v2/app"
    assert stub.calls[1]["params"] == {"page_size": 1, "page_token": "app_2"}
    assert stub.calls[2]["path"] == "/search/v2/message"
    assert stub.calls[3]["params"] == {"page_size": 1, "page_token": "msg_2"}
    assert stub.calls[4]["path"] == "/search/v2/doc_wiki/search"
    assert stub.calls[4]["payload"] == {"query": "weekly", "page_size": 1}
    assert stub.calls[5]["payload"] == {"query": "weekly", "page_token": "doc_2", "page_size": 1}
