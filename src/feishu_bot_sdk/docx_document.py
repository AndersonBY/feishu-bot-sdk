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


class DocxDocumentService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def create_document(self, title: str, *, folder_token: Optional[str] = None) -> Mapping[str, Any]:
        payload: dict[str, object] = {"title": title}
        effective_folder_token = folder_token or self._client.config.doc_folder_token
        if effective_folder_token:
            payload["folder_token"] = effective_folder_token
        response = self._client.request_json("POST", "/docx/v1/documents", payload=payload)
        return _unwrap_data(response)

    def get_document(self, document_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/docx/v1/documents/{document_id}")
        return _unwrap_data(response)

    def get_raw_content(self, document_id: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/docx/v1/documents/{document_id}/raw_content")
        return _unwrap_data(response)

    def list_blocks(
        self,
        document_id: str,
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
            f"/docx/v1/documents/{document_id}/blocks",
            params=params,
        )
        return _unwrap_data(response)

    def iter_blocks(
        self,
        document_id: str,
        *,
        page_size: int = 500,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_blocks(
                document_id,
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


class AsyncDocxDocumentService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def create_document(
        self,
        title: str,
        *,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {"title": title}
        effective_folder_token = folder_token or self._client.config.doc_folder_token
        if effective_folder_token:
            payload["folder_token"] = effective_folder_token
        response = await self._client.request_json("POST", "/docx/v1/documents", payload=payload)
        return _unwrap_data(response)

    async def get_document(self, document_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/docx/v1/documents/{document_id}")
        return _unwrap_data(response)

    async def get_raw_content(self, document_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/docx/v1/documents/{document_id}/raw_content",
        )
        return _unwrap_data(response)

    async def list_blocks(
        self,
        document_id: str,
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
            f"/docx/v1/documents/{document_id}/blocks",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_blocks(
        self,
        document_id: str,
        *,
        page_size: int = 500,
        document_revision_id: Optional[int] = None,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_blocks(
                document_id,
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
