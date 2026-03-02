from typing import Any, AsyncIterator, Iterator, Mapping, Optional, Sequence

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _iter_page_items(data: Mapping[str, Any], *, key: str = "items") -> Iterator[Mapping[str, Any]]:
    items = data.get(key)
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, Mapping):
            yield item


def _iter_scope_items(data: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    for scope_type, field in (("user", "user_ids"), ("department", "department_ids"), ("group", "group_ids")):
        values = data.get(field)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value:
                yield {"scope_type": scope_type, "scope_id": value}


def _next_page_token(data: Mapping[str, Any]) -> Optional[str]:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _normalize_ids(values: Sequence[str], *, name: str) -> list[str]:
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        normalized.append(text)
    if not normalized:
        raise ValueError(f"{name} must contain at least one non-empty value")
    return normalized


class ContactService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_user(
        self,
        user_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/contact/v3/users/{user_id}",
            params=params,
        )
        return _unwrap_data(response)

    def batch_get_users(
        self,
        user_ids: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_ids": _normalize_ids(user_ids, name="user_ids"),
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = self._client.request_json("GET", "/contact/v3/users/batch", params=params)
        return _unwrap_data(response)

    def batch_get_user_ids(
        self,
        *,
        emails: Optional[Sequence[str]] = None,
        mobiles: Optional[Sequence[str]] = None,
        include_resigned: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "emails": list(emails) if emails is not None else None,
                "mobiles": list(mobiles) if mobiles is not None else None,
                "include_resigned": include_resigned,
            }
        )
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/contact/v3/users/batch_get_id",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def find_users_by_department(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "department_id": department_id,
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json("GET", "/contact/v3/users/find_by_department", params=params)
        return _unwrap_data(response)

    def iter_users_by_department(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.find_users_by_department(
                department_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def search_users(
        self,
        query: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "query": query,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json("GET", "/search/v1/user", params=params)
        return _unwrap_data(response)

    def iter_search_users(self, query: str, *, page_size: int = 50) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.search_users(query, page_size=page_size, page_token=page_token)
            yield from _iter_page_items(data, key="users")
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_department(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/contact/v3/departments/{department_id}",
            params=params,
        )
        return _unwrap_data(response)

    def list_department_children(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        fetch_child: Optional[bool] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "fetch_child": fetch_child,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/contact/v3/departments/{department_id}/children",
            params=params,
        )
        return _unwrap_data(response)

    def iter_department_children(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        fetch_child: Optional[bool] = None,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_department_children(
                department_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                fetch_child=fetch_child,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def search_departments(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "POST",
            "/contact/v3/departments/search",
            params=params,
            payload={"query": query},
        )
        return _unwrap_data(response)

    def iter_search_departments(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.search_departments(
                query,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def batch_get_departments(
        self,
        department_ids: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "department_ids": _normalize_ids(department_ids, name="department_ids"),
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = self._client.request_json("GET", "/contact/v3/departments/batch", params=params)
        return _unwrap_data(response)

    def list_parent_departments(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "department_id": department_id,
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json("GET", "/contact/v3/departments/parent", params=params)
        return _unwrap_data(response)

    def iter_parent_departments(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_parent_departments(
                department_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def list_scopes(
        self,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json("GET", "/contact/v3/scopes", params=params)
        return _unwrap_data(response)

    def iter_scopes(
        self,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_scopes(
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_scope_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return


class AsyncContactService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_user(
        self,
        user_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/contact/v3/users/{user_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def batch_get_users(
        self,
        user_ids: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_ids": _normalize_ids(user_ids, name="user_ids"),
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = await self._client.request_json("GET", "/contact/v3/users/batch", params=params)
        return _unwrap_data(response)

    async def batch_get_user_ids(
        self,
        *,
        emails: Optional[Sequence[str]] = None,
        mobiles: Optional[Sequence[str]] = None,
        include_resigned: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "emails": list(emails) if emails is not None else None,
                "mobiles": list(mobiles) if mobiles is not None else None,
                "include_resigned": include_resigned,
            }
        )
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/contact/v3/users/batch_get_id",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def find_users_by_department(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "department_id": department_id,
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/contact/v3/users/find_by_department", params=params)
        return _unwrap_data(response)

    async def iter_users_by_department(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.find_users_by_department(
                department_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def search_users(
        self,
        query: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "query": query,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/search/v1/user", params=params)
        return _unwrap_data(response)

    async def iter_search_users(self, query: str, *, page_size: int = 50) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_users(query, page_size=page_size, page_token=page_token)
            for item in _iter_page_items(data, key="users"):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_department(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/contact/v3/departments/{department_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def list_department_children(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        fetch_child: Optional[bool] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "fetch_child": fetch_child,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/contact/v3/departments/{department_id}/children",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_department_children(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        fetch_child: Optional[bool] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_department_children(
                department_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                fetch_child=fetch_child,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def search_departments(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "POST",
            "/contact/v3/departments/search",
            params=params,
            payload={"query": query},
        )
        return _unwrap_data(response)

    async def iter_search_departments(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_departments(
                query,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def batch_get_departments(
        self,
        department_ids: Sequence[str],
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "department_ids": _normalize_ids(department_ids, name="department_ids"),
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
            }
        )
        response = await self._client.request_json("GET", "/contact/v3/departments/batch", params=params)
        return _unwrap_data(response)

    async def list_parent_departments(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "department_id": department_id,
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/contact/v3/departments/parent", params=params)
        return _unwrap_data(response)

    async def iter_parent_departments(
        self,
        department_id: str,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_parent_departments(
                department_id,
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def list_scopes(
        self,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "department_id_type": department_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json("GET", "/contact/v3/scopes", params=params)
        return _unwrap_data(response)

    async def iter_scopes(
        self,
        *,
        user_id_type: Optional[str] = None,
        department_id_type: Optional[str] = None,
        page_size: int = 50,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_scopes(
                user_id_type=user_id_type,
                department_id_type=department_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_scope_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return
