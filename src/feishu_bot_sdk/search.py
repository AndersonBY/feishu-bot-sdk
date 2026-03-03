from typing import Any, AsyncIterator, Iterator, Mapping, Optional, Sequence

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _iter_page_items(data: Mapping[str, Any], *, key: str = "items") -> Iterator[Any]:
    items = data.get(key)
    if not isinstance(items, list):
        return
    for item in items:
        yield item


def _next_page_token(data: Mapping[str, Any]) -> Optional[str]:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _normalize_sequence(values: Optional[Sequence[str]]) -> Optional[list[str]]:
    if values is None:
        return None
    normalized = [str(value).strip() for value in values if str(value).strip()]
    if not normalized:
        return None
    return normalized


class SearchService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def search_apps(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "POST",
            "/search/v2/app",
            params=params,
            payload={"query": query},
        )
        return _unwrap_data(response)

    def iter_search_apps(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 20,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.search_apps(
                query,
                user_id_type=user_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data, key="items")
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def search_messages(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        from_ids: Optional[Sequence[str]] = None,
        chat_ids: Optional[Sequence[str]] = None,
        message_type: Optional[str] = None,
        at_chatter_ids: Optional[Sequence[str]] = None,
        from_type: Optional[str] = None,
        chat_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        payload = _drop_none(
            {
                "query": query,
                "from_ids": _normalize_sequence(from_ids),
                "chat_ids": _normalize_sequence(chat_ids),
                "message_type": message_type,
                "at_chatter_ids": _normalize_sequence(at_chatter_ids),
                "from_type": from_type,
                "chat_type": chat_type,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        response = self._client.request_json(
            "POST",
            "/search/v2/message",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def iter_search_messages(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 20,
        from_ids: Optional[Sequence[str]] = None,
        chat_ids: Optional[Sequence[str]] = None,
        message_type: Optional[str] = None,
        at_chatter_ids: Optional[Sequence[str]] = None,
        from_type: Optional[str] = None,
        chat_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.search_messages(
                query,
                user_id_type=user_id_type,
                page_size=page_size,
                page_token=page_token,
                from_ids=from_ids,
                chat_ids=chat_ids,
                message_type=message_type,
                at_chatter_ids=at_chatter_ids,
                from_type=from_type,
                chat_type=chat_type,
                start_time=start_time,
                end_time=end_time,
            )
            yield from _iter_page_items(data, key="items")
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def search_doc_wiki(
        self,
        query: str,
        *,
        doc_filter: Optional[Mapping[str, object]] = None,
        wiki_filter: Optional[Mapping[str, object]] = None,
        page_token: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "query": query,
                "doc_filter": dict(doc_filter) if doc_filter is not None else None,
                "wiki_filter": dict(wiki_filter) if wiki_filter is not None else None,
                "page_token": page_token,
                "page_size": page_size,
            }
        )
        response = self._client.request_json(
            "POST",
            "/search/v2/doc_wiki/search",
            payload=payload,
        )
        return _unwrap_data(response)

    def iter_search_doc_wiki(
        self,
        query: str,
        *,
        doc_filter: Optional[Mapping[str, object]] = None,
        wiki_filter: Optional[Mapping[str, object]] = None,
        page_size: int = 20,
    ) -> Iterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = self.search_doc_wiki(
                query,
                doc_filter=doc_filter,
                wiki_filter=wiki_filter,
                page_token=page_token,
                page_size=page_size,
            )
            yield from _iter_page_items(data, key="res_units")
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return


class AsyncSearchService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def search_apps(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "POST",
            "/search/v2/app",
            params=params,
            payload={"query": query},
        )
        return _unwrap_data(response)

    async def iter_search_apps(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 20,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_apps(
                query,
                user_id_type=user_id_type,
                page_size=page_size,
                page_token=page_token,
            )
            for item in _iter_page_items(data, key="items"):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def search_messages(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        from_ids: Optional[Sequence[str]] = None,
        chat_ids: Optional[Sequence[str]] = None,
        message_type: Optional[str] = None,
        at_chatter_ids: Optional[Sequence[str]] = None,
        from_type: Optional[str] = None,
        chat_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        payload = _drop_none(
            {
                "query": query,
                "from_ids": _normalize_sequence(from_ids),
                "chat_ids": _normalize_sequence(chat_ids),
                "message_type": message_type,
                "at_chatter_ids": _normalize_sequence(at_chatter_ids),
                "from_type": from_type,
                "chat_type": chat_type,
                "start_time": start_time,
                "end_time": end_time,
            }
        )
        response = await self._client.request_json(
            "POST",
            "/search/v2/message",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def iter_search_messages(
        self,
        query: str,
        *,
        user_id_type: Optional[str] = None,
        page_size: int = 20,
        from_ids: Optional[Sequence[str]] = None,
        chat_ids: Optional[Sequence[str]] = None,
        message_type: Optional[str] = None,
        at_chatter_ids: Optional[Sequence[str]] = None,
        from_type: Optional[str] = None,
        chat_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_messages(
                query,
                user_id_type=user_id_type,
                page_size=page_size,
                page_token=page_token,
                from_ids=from_ids,
                chat_ids=chat_ids,
                message_type=message_type,
                at_chatter_ids=at_chatter_ids,
                from_type=from_type,
                chat_type=chat_type,
                start_time=start_time,
                end_time=end_time,
            )
            for item in _iter_page_items(data, key="items"):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def search_doc_wiki(
        self,
        query: str,
        *,
        doc_filter: Optional[Mapping[str, object]] = None,
        wiki_filter: Optional[Mapping[str, object]] = None,
        page_token: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "query": query,
                "doc_filter": dict(doc_filter) if doc_filter is not None else None,
                "wiki_filter": dict(wiki_filter) if wiki_filter is not None else None,
                "page_token": page_token,
                "page_size": page_size,
            }
        )
        response = await self._client.request_json(
            "POST",
            "/search/v2/doc_wiki/search",
            payload=payload,
        )
        return _unwrap_data(response)

    async def iter_search_doc_wiki(
        self,
        query: str,
        *,
        doc_filter: Optional[Mapping[str, object]] = None,
        wiki_filter: Optional[Mapping[str, object]] = None,
        page_size: int = 20,
    ) -> AsyncIterator[Any]:
        page_token: Optional[str] = None
        while True:
            data = await self.search_doc_wiki(
                query,
                doc_filter=doc_filter,
                wiki_filter=wiki_filter,
                page_token=page_token,
                page_size=page_size,
            )
            for item in _iter_page_items(data, key="res_units"):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return
