from typing import Any, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _extract_content(data: Mapping[str, Any]) -> str:
    content = data.get("content")
    if isinstance(content, str):
        return content
    return ""


class DocContentService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def get_content(
        self,
        doc_token: str,
        *,
        doc_type: str = "docx",
        content_type: str = "markdown",
        lang: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "doc_token": doc_token,
                "doc_type": doc_type,
                "content_type": content_type,
                "lang": lang,
            }
        )
        response = self._client.request_json("GET", "/docs/v1/content", params=params)
        return _unwrap_data(response)

    def get_markdown(
        self,
        doc_token: str,
        *,
        doc_type: str = "docx",
        lang: Optional[str] = None,
    ) -> str:
        data = self.get_content(
            doc_token,
            doc_type=doc_type,
            content_type="markdown",
            lang=lang,
        )
        return _extract_content(data)


class AsyncDocContentService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def get_content(
        self,
        doc_token: str,
        *,
        doc_type: str = "docx",
        content_type: str = "markdown",
        lang: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "doc_token": doc_token,
                "doc_type": doc_type,
                "content_type": content_type,
                "lang": lang,
            }
        )
        response = await self._client.request_json("GET", "/docs/v1/content", params=params)
        return _unwrap_data(response)

    async def get_markdown(
        self,
        doc_token: str,
        *,
        doc_type: str = "docx",
        lang: Optional[str] = None,
    ) -> str:
        data = await self.get_content(
            doc_token,
            doc_type=doc_type,
            content_type="markdown",
            lang=lang,
        )
        return _extract_content(data)
