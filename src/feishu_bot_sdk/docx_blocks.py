from typing import Any, AsyncIterator, Dict, Iterator, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> Dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _iter_items(data: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    items = data.get("items")
    if not isinstance(items, list):
        return
    for item in items:
        if isinstance(item, Mapping):
            yield item


def _next_page_token(data: Mapping[str, Any]) -> Optional[str]:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


class DocxBlockService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_block(
        self,
        document_id: str,
        block_id: str,
        *,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}",
            params=params,
        )
        return _unwrap_data(response)

    def list_children(
        self,
        document_id: str,
        block_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "document_revision_id": document_revision_id,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/children",
            params=params,
        )
        return _unwrap_data(response)

    def iter_children(
        self,
        document_id: str,
        block_id: str,
        *,
        page_size: int = 500,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_children(
                document_id,
                block_id,
                page_size=page_size,
                page_token=page_token,
                document_revision_id=document_revision_id,
                user_id_type=user_id_type,
            )
            yield from _iter_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_children(
        self,
        document_id: str,
        block_id: str,
        *,
        children: list[Mapping[str, object]],
        index: int = -1,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/children",
            params=params,
            payload={"index": index, "children": [dict(child) for child in children]},
        )
        return _unwrap_data(response)

    def create_descendant(
        self,
        document_id: str,
        block_id: str,
        *,
        children_id: list[str],
        descendants: list[Mapping[str, object]],
        index: int = -1,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        payload = {
            "index": index,
            "children_id": list(children_id),
            "descendants": [dict(block) for block in descendants],
        }
        response = self._client.request_json(
            "POST",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/descendant",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def update_block(
        self,
        document_id: str,
        block_id: str,
        *,
        operations: Mapping[str, object],
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "PATCH",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}",
            params=params,
            payload=dict(operations),
        )
        return _unwrap_data(response)

    def batch_update(
        self,
        document_id: str,
        *,
        requests: list[Mapping[str, object]],
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "PATCH",
            f"/docx/v1/documents/{document_id}/blocks/batch_update",
            params=params,
            payload={"requests": [dict(request) for request in requests]},
        )
        return _unwrap_data(response)

    def delete_children_range(
        self,
        document_id: str,
        block_id: str,
        *,
        start_index: int,
        end_index: int,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
            }
        )
        response = self._client.request_json(
            "DELETE",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/children/batch_delete",
            params=params,
            payload={"start_index": start_index, "end_index": end_index},
        )
        return _unwrap_data(response)

    def convert_content(
        self,
        content: str,
        *,
        content_type: str = "markdown",
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/docx/v1/documents/blocks/convert",
            payload={
                "content_type": content_type,
                "content": content,
            },
        )
        return _unwrap_data(response)


class AsyncDocxBlockService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_block(
        self,
        document_id: str,
        block_id: str,
        *,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def list_children(
        self,
        document_id: str,
        block_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "document_revision_id": document_revision_id,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/children",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_children(
        self,
        document_id: str,
        block_id: str,
        *,
        page_size: int = 500,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_children(
                document_id,
                block_id,
                page_size=page_size,
                page_token=page_token,
                document_revision_id=document_revision_id,
                user_id_type=user_id_type,
            )
            for item in _iter_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def create_children(
        self,
        document_id: str,
        block_id: str,
        *,
        children: list[Mapping[str, object]],
        index: int = -1,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/children",
            params=params,
            payload={"index": index, "children": [dict(child) for child in children]},
        )
        return _unwrap_data(response)

    async def create_descendant(
        self,
        document_id: str,
        block_id: str,
        *,
        children_id: list[str],
        descendants: list[Mapping[str, object]],
        index: int = -1,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        payload = {
            "index": index,
            "children_id": list(children_id),
            "descendants": [dict(block) for block in descendants],
        }
        response = await self._client.request_json(
            "POST",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/descendant",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def update_block(
        self,
        document_id: str,
        block_id: str,
        *,
        operations: Mapping[str, object],
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "PATCH",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}",
            params=params,
            payload=dict(operations),
        )
        return _unwrap_data(response)

    async def batch_update(
        self,
        document_id: str,
        *,
        requests: list[Mapping[str, object]],
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "PATCH",
            f"/docx/v1/documents/{document_id}/blocks/batch_update",
            params=params,
            payload={"requests": [dict(request) for request in requests]},
        )
        return _unwrap_data(response)

    async def delete_children_range(
        self,
        document_id: str,
        block_id: str,
        *,
        start_index: int,
        end_index: int,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "document_revision_id": document_revision_id,
                "client_token": client_token,
            }
        )
        response = await self._client.request_json(
            "DELETE",
            f"/docx/v1/documents/{document_id}/blocks/{block_id}/children/batch_delete",
            params=params,
            payload={"start_index": start_index, "end_index": end_index},
        )
        return _unwrap_data(response)

    async def convert_content(
        self,
        content: str,
        *,
        content_type: str = "markdown",
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/docx/v1/documents/blocks/convert",
            payload={
                "content_type": content_type,
                "content": content,
            },
        )
        return _unwrap_data(response)
