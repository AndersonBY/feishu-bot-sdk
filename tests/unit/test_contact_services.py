import asyncio
from typing import Any, Mapping, Optional, cast

from feishu_bot_sdk.contact import AsyncContactService, ContactService
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


def test_contact_user_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = ContactService(cast(FeishuClient, stub))

    service.get_user("ou_1", user_id_type="open_id", department_id_type="open_department_id")
    service.batch_get_users(
        ["ou_1", "ou_2"],
        user_id_type="open_id",
        department_id_type="open_department_id",
    )
    service.batch_get_user_ids(
        emails=["a@example.com"],
        mobiles=["13800138000"],
        include_resigned=True,
        user_id_type="open_id",
    )
    service.find_users_by_department(
        "od_1",
        user_id_type="open_id",
        department_id_type="open_department_id",
        page_size=10,
        page_token="u_next",
    )
    service.search_users("alice", page_size=20, page_token="s_next")

    assert len(stub.calls) == 5
    assert stub.calls[0]["path"] == "/contact/v3/users/ou_1"
    assert stub.calls[0]["params"] == {
        "user_id_type": "open_id",
        "department_id_type": "open_department_id",
    }
    assert stub.calls[1]["path"] == "/contact/v3/users/batch"
    assert stub.calls[1]["params"] == {
        "user_ids": ["ou_1", "ou_2"],
        "user_id_type": "open_id",
        "department_id_type": "open_department_id",
    }
    assert stub.calls[2]["method"] == "POST"
    assert stub.calls[2]["path"] == "/contact/v3/users/batch_get_id"
    assert stub.calls[2]["params"] == {"user_id_type": "open_id"}
    assert stub.calls[2]["payload"] == {
        "emails": ["a@example.com"],
        "mobiles": ["13800138000"],
        "include_resigned": True,
    }
    assert stub.calls[3]["path"] == "/contact/v3/users/find_by_department"
    assert stub.calls[3]["params"]["department_id"] == "od_1"
    assert stub.calls[4]["path"] == "/search/v1/user"
    assert stub.calls[4]["params"] == {"query": "alice", "page_size": 20, "page_token": "s_next"}


def test_contact_department_and_scope_requests() -> None:
    def resolver(_call: Mapping[str, Any]) -> Mapping[str, Any]:
        return {"code": 0, "data": {"ok": True}}

    stub = _SyncClientStub(resolver)
    service = ContactService(cast(FeishuClient, stub))

    service.get_department("od_1", user_id_type="open_id", department_id_type="open_department_id")
    service.list_department_children(
        "od_1",
        user_id_type="open_id",
        department_id_type="open_department_id",
        fetch_child=True,
        page_size=5,
        page_token="d_next",
    )
    service.search_departments(
        "研发",
        user_id_type="open_id",
        department_id_type="open_department_id",
        page_size=10,
        page_token="dp_1",
    )
    service.batch_get_departments(
        ["od_1", "od_2"],
        user_id_type="open_id",
        department_id_type="open_department_id",
    )
    service.list_parent_departments(
        "od_1",
        user_id_type="open_id",
        department_id_type="open_department_id",
        page_size=10,
        page_token="p_1",
    )
    service.list_scopes(
        user_id_type="open_id",
        department_id_type="open_department_id",
        page_size=100,
        page_token="scope_next",
    )

    assert len(stub.calls) == 6
    assert stub.calls[0]["path"] == "/contact/v3/departments/od_1"
    assert stub.calls[1]["path"] == "/contact/v3/departments/od_1/children"
    assert stub.calls[1]["params"]["fetch_child"] is True
    assert stub.calls[2]["path"] == "/contact/v3/departments/search"
    assert stub.calls[2]["payload"] == {"query": "研发"}
    assert stub.calls[3]["path"] == "/contact/v3/departments/batch"
    assert stub.calls[3]["params"]["department_ids"] == ["od_1", "od_2"]
    assert stub.calls[4]["path"] == "/contact/v3/departments/parent"
    assert stub.calls[4]["params"]["department_id"] == "od_1"
    assert stub.calls[5]["path"] == "/contact/v3/scopes"
    assert stub.calls[5]["params"]["page_size"] == 100


def test_async_contact_iterators() -> None:
    def resolver(call: Mapping[str, Any]) -> Mapping[str, Any]:
        path = str(call["path"])
        params = call["params"]
        page_token = params.get("page_token")
        if path == "/contact/v3/users/find_by_department":
            if page_token == "u2":
                return {"code": 0, "data": {"items": [{"user_id": "u_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"user_id": "u_1"}], "has_more": True, "page_token": "u2"},
            }
        if path == "/search/v1/user":
            if page_token == "s2":
                return {"code": 0, "data": {"users": [{"open_id": "ou_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"users": [{"open_id": "ou_1"}], "has_more": True, "page_token": "s2"},
            }
        if path.endswith("/children"):
            if page_token == "c2":
                return {"code": 0, "data": {"items": [{"department_id": "od_2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"department_id": "od_1"}], "has_more": True, "page_token": "c2"},
            }
        if path == "/contact/v3/departments/search":
            if page_token == "d2":
                return {"code": 0, "data": {"items": [{"department_id": "od_4"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"department_id": "od_3"}], "has_more": True, "page_token": "d2"},
            }
        if path == "/contact/v3/departments/parent":
            if page_token == "p2":
                return {"code": 0, "data": {"items": [{"department_id": "od_p2"}], "has_more": False}}
            return {
                "code": 0,
                "data": {"items": [{"department_id": "od_p1"}], "has_more": True, "page_token": "p2"},
            }
        if path == "/contact/v3/scopes":
            if page_token == "scope2":
                return {"code": 0, "data": {"group_ids": ["g_1"], "has_more": False}}
            return {
                "code": 0,
                "data": {
                    "user_ids": ["ou_1"],
                    "department_ids": ["od_1"],
                    "has_more": True,
                    "page_token": "scope2",
                },
            }
        return {"code": 0, "data": {"ok": True}}

    stub = _AsyncClientStub(resolver)
    service = AsyncContactService(cast(AsyncFeishuClient, stub))

    async def run() -> None:
        users_by_department = [item async for item in service.iter_users_by_department("od_root", page_size=1)]
        users_search = [item async for item in service.iter_search_users("alice", page_size=1)]
        children = [item async for item in service.iter_department_children("od_root", page_size=1)]
        departments_search = [item async for item in service.iter_search_departments("dev", page_size=1)]
        parents = [item async for item in service.iter_parent_departments("od_root", page_size=1)]
        scopes = [item async for item in service.iter_scopes(page_size=2)]

        assert users_by_department == [{"user_id": "u_1"}, {"user_id": "u_2"}]
        assert users_search == [{"open_id": "ou_1"}, {"open_id": "ou_2"}]
        assert children == [{"department_id": "od_1"}, {"department_id": "od_2"}]
        assert departments_search == [{"department_id": "od_3"}, {"department_id": "od_4"}]
        assert parents == [{"department_id": "od_p1"}, {"department_id": "od_p2"}]
        assert scopes == [
            {"scope_type": "user", "scope_id": "ou_1"},
            {"scope_type": "department", "scope_id": "od_1"},
            {"scope_type": "group", "scope_id": "g_1"},
        ]

    asyncio.run(run())
