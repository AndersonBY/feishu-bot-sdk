from __future__ import annotations

import copy
import mimetypes
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, cast
from urllib.parse import unquote, urlparse

import httpx

from ..drive import (
    AsyncDriveFileService,
    AsyncDrivePermissionService,
    DriveFileService,
    DrivePermissionService,
)
from ..exceptions import FeishuError
from ..feishu import AsyncFeishuClient, FeishuClient
from ..types import DriveResourceType, MemberIdType
from .blocks import AsyncDocxBlockService, DocxBlockService
from .content import AsyncDocContentService, DocContentService
from .document import AsyncDocxDocumentService, DocxDocumentService


_INSERT_BATCH_LIMIT = 1000


@dataclass(frozen=True)
class _DownloadedAsset:
    content: bytes
    file_name: str
    content_type: Optional[str]


@dataclass(frozen=True)
class _InsertBatch:
    root_ids: List[str]
    blocks: List[Dict[str, Any]]
    image_urls: Dict[str, str]


class DocxService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client
        self._documents = DocxDocumentService(feishu_client)
        self._blocks = DocxBlockService(feishu_client)
        self._content = DocContentService(feishu_client)
        self._drive_files = DriveFileService(feishu_client)
        self._drive_permissions = DrivePermissionService(feishu_client)

    def create_document(
        self,
        title: str,
        *,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        data = self._documents.create_document(title, folder_token=folder_token)
        document_id = _extract_document_id(data)
        result = dict(data)
        result["document_id"] = document_id
        result["url"] = _build_document_url(self._client, document_id)
        return result

    def append_markdown(self, document_id: str, markdown_text: str) -> Mapping[str, Any]:
        return self.insert_content(
            document_id,
            markdown_text,
            content_type="markdown",
        )

    def insert_content(
        self,
        document_id: str,
        content: str,
        *,
        block_id: Optional[str] = None,
        content_type: str = "markdown",
        index: int = -1,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
        content_base_dir: str | os.PathLike[str] | None = None,
    ) -> Mapping[str, Any]:
        if not content:
            raise ValueError("content must not be empty")
        converted = self._blocks.convert_content(content, content_type=content_type)
        target_block_id = block_id or document_id
        batches = _build_insert_batches(converted, limit=_INSERT_BATCH_LIMIT)
        if not batches:
            raise FeishuError("docx convert returned no insertable blocks")

        current_index = index
        inserted_batches: List[Mapping[str, Any]] = []
        image_replacements: List[Mapping[str, Any]] = []
        for batch in batches:
            inserted = self._blocks.create_descendant(
                document_id,
                target_block_id,
                children_id=batch.root_ids,
                descendants=cast(List[Mapping[str, object]], batch.blocks),
                index=current_index,
                document_revision_id=document_revision_id,
                client_token=client_token,
                user_id_type=user_id_type,
            )
            inserted_batches.append(inserted)
            if batch.image_urls:
                image_replacements.extend(
                    self._replace_inserted_images(
                        document_id,
                        inserted,
                        batch.image_urls,
                        document_revision_id=document_revision_id,
                        client_token=client_token,
                        user_id_type=user_id_type,
                        content_base_dir=content_base_dir,
                    )
                )
            if current_index >= 0:
                current_index += len(batch.root_ids)

        return {
            "document_id": document_id,
            "block_id": target_block_id,
            "content_type": content_type,
            "batch_count": len(inserted_batches),
            "converted": converted,
            "inserted_batches": inserted_batches,
            "image_replacements": image_replacements,
        }

    def set_title(
        self,
        document_id: str,
        title: str,
        *,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self.set_block_text(
            document_id,
            document_id,
            title,
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    def set_block_text(
        self,
        document_id: str,
        block_id: str,
        text: str,
        *,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        if not text:
            raise ValueError("text must not be empty")
        return self._blocks.update_block(
            document_id,
            block_id,
            operations={"update_text_elements": {"elements": _text_elements(text)}},
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    def replace_image(
        self,
        document_id: str,
        block_id: str,
        *,
        file_path: Optional[str] = None,
        content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self._replace_asset(
            document_id,
            block_id,
            operation_name="replace_image",
            parent_type="docx_image",
            default_file_name="image.png",
            file_path=file_path,
            content=content,
            file_name=file_name,
            checksum=checksum,
            content_type=content_type,
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    def replace_file(
        self,
        document_id: str,
        block_id: str,
        *,
        file_path: Optional[str] = None,
        content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self._replace_asset(
            document_id,
            block_id,
            operation_name="replace_file",
            parent_type="docx_file",
            default_file_name="attachment.bin",
            file_path=file_path,
            content=content,
            file_name=file_name,
            checksum=checksum,
            content_type=content_type,
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    def get_content(
        self,
        doc_token: str,
        *,
        doc_type: str = "docx",
        content_type: str = "markdown",
        lang: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return self._content.get_content(
            doc_token,
            doc_type=doc_type,
            content_type=content_type,
            lang=lang,
        )

    def grant_edit_permission(
        self,
        document_id: str,
        member_id: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
    ) -> None:
        self._drive_permissions.grant_edit_permission(
            document_id,
            member_id,
            member_id_type,
            resource_type=DriveResourceType.DOCX,
            permission=self._client.config.member_permission,
        )

    def _replace_inserted_images(
        self,
        document_id: str,
        inserted: Mapping[str, Any],
        image_urls_by_temp_id: Mapping[str, str],
        *,
        document_revision_id: Optional[int],
        client_token: Optional[str],
        user_id_type: Optional[str],
        content_base_dir: str | os.PathLike[str] | None = None,
    ) -> List[Mapping[str, Any]]:
        relations = _extract_relation_map(inserted)
        replacements: List[Mapping[str, Any]] = []
        for temp_block_id, image_url in image_urls_by_temp_id.items():
            block_id = relations.get(temp_block_id)
            if not block_id:
                raise FeishuError(f"docx insert response missing block relation for image block {temp_block_id}")
            downloaded = _download_binary(image_url, base_dir=content_base_dir)
            replacement = self.replace_image(
                document_id,
                block_id,
                content=downloaded.content,
                file_name=downloaded.file_name,
                content_type=downloaded.content_type,
                document_revision_id=document_revision_id,
                client_token=client_token,
                user_id_type=user_id_type,
            )
            item = {
                "temporary_block_id": temp_block_id,
                "block_id": block_id,
                "image_url": image_url,
                "result": replacement,
            }
            file_token = replacement.get("file_token")
            if isinstance(file_token, str) and file_token:
                item["file_token"] = file_token
            replacements.append(item)
        return replacements

    def _replace_asset(
        self,
        document_id: str,
        block_id: str,
        *,
        operation_name: str,
        parent_type: str,
        default_file_name: str,
        file_path: Optional[str],
        content: Optional[bytes],
        file_name: Optional[str],
        checksum: Optional[str],
        content_type: Optional[str],
        document_revision_id: Optional[int],
        client_token: Optional[str],
        user_id_type: Optional[str],
    ) -> Mapping[str, Any]:
        if bool(file_path) == bool(content is not None):
            raise ValueError("exactly one of file_path or content is required")

        if file_path is not None:
            upload = self._drive_files.upload_media(
                file_path,
                parent_type=parent_type,
                parent_node=block_id,
                file_name=file_name,
                checksum=checksum,
                content_type=content_type,
            )
        else:
            upload = self._drive_files.upload_media_bytes(
                file_name or default_file_name,
                content or b"",
                parent_type=parent_type,
                parent_node=block_id,
                checksum=checksum,
                content_type=content_type,
            )

        file_token = _extract_file_token(upload)
        update = self._blocks.update_block(
            document_id,
            block_id,
            operations={operation_name: {"token": file_token}},
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )
        return {
            "document_id": document_id,
            "block_id": block_id,
            "file_token": file_token,
            "upload": upload,
            "update": update,
        }


class AsyncDocxService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client
        self._documents = AsyncDocxDocumentService(feishu_client)
        self._blocks = AsyncDocxBlockService(feishu_client)
        self._content = AsyncDocContentService(feishu_client)
        self._drive_files = AsyncDriveFileService(feishu_client)
        self._drive_permissions = AsyncDrivePermissionService(feishu_client)

    async def create_document(
        self,
        title: str,
        *,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        data = await self._documents.create_document(title, folder_token=folder_token)
        document_id = _extract_document_id(data)
        result = dict(data)
        result["document_id"] = document_id
        result["url"] = _build_document_url(self._client, document_id)
        return result

    async def append_markdown(self, document_id: str, markdown_text: str) -> Mapping[str, Any]:
        return await self.insert_content(
            document_id,
            markdown_text,
            content_type="markdown",
        )

    async def insert_content(
        self,
        document_id: str,
        content: str,
        *,
        block_id: Optional[str] = None,
        content_type: str = "markdown",
        index: int = -1,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
        content_base_dir: str | os.PathLike[str] | None = None,
    ) -> Mapping[str, Any]:
        if not content:
            raise ValueError("content must not be empty")
        converted = await self._blocks.convert_content(content, content_type=content_type)
        target_block_id = block_id or document_id
        batches = _build_insert_batches(converted, limit=_INSERT_BATCH_LIMIT)
        if not batches:
            raise FeishuError("docx convert returned no insertable blocks")

        current_index = index
        inserted_batches: List[Mapping[str, Any]] = []
        image_replacements: List[Mapping[str, Any]] = []
        for batch in batches:
            inserted = await self._blocks.create_descendant(
                document_id,
                target_block_id,
                children_id=batch.root_ids,
                descendants=cast(List[Mapping[str, object]], batch.blocks),
                index=current_index,
                document_revision_id=document_revision_id,
                client_token=client_token,
                user_id_type=user_id_type,
            )
            inserted_batches.append(inserted)
            if batch.image_urls:
                image_replacements.extend(
                    await self._replace_inserted_images(
                        document_id,
                        inserted,
                        batch.image_urls,
                        document_revision_id=document_revision_id,
                        client_token=client_token,
                        user_id_type=user_id_type,
                        content_base_dir=content_base_dir,
                    )
                )
            if current_index >= 0:
                current_index += len(batch.root_ids)

        return {
            "document_id": document_id,
            "block_id": target_block_id,
            "content_type": content_type,
            "batch_count": len(inserted_batches),
            "converted": converted,
            "inserted_batches": inserted_batches,
            "image_replacements": image_replacements,
        }

    async def set_title(
        self,
        document_id: str,
        title: str,
        *,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self.set_block_text(
            document_id,
            document_id,
            title,
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    async def set_block_text(
        self,
        document_id: str,
        block_id: str,
        text: str,
        *,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        if not text:
            raise ValueError("text must not be empty")
        return await self._blocks.update_block(
            document_id,
            block_id,
            operations={"update_text_elements": {"elements": _text_elements(text)}},
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    async def replace_image(
        self,
        document_id: str,
        block_id: str,
        *,
        file_path: Optional[str] = None,
        content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self._replace_asset(
            document_id,
            block_id,
            operation_name="replace_image",
            parent_type="docx_image",
            default_file_name="image.png",
            file_path=file_path,
            content=content,
            file_name=file_name,
            checksum=checksum,
            content_type=content_type,
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    async def replace_file(
        self,
        document_id: str,
        block_id: str,
        *,
        file_path: Optional[str] = None,
        content: Optional[bytes] = None,
        file_name: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
        document_revision_id: Optional[int] = None,
        client_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self._replace_asset(
            document_id,
            block_id,
            operation_name="replace_file",
            parent_type="docx_file",
            default_file_name="attachment.bin",
            file_path=file_path,
            content=content,
            file_name=file_name,
            checksum=checksum,
            content_type=content_type,
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )

    async def get_content(
        self,
        doc_token: str,
        *,
        doc_type: str = "docx",
        content_type: str = "markdown",
        lang: Optional[str] = None,
    ) -> Mapping[str, Any]:
        return await self._content.get_content(
            doc_token,
            doc_type=doc_type,
            content_type=content_type,
            lang=lang,
        )

    async def grant_edit_permission(
        self,
        document_id: str,
        member_id: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
    ) -> None:
        await self._drive_permissions.grant_edit_permission(
            document_id,
            member_id,
            member_id_type,
            resource_type=DriveResourceType.DOCX,
            permission=self._client.config.member_permission,
        )

    async def _replace_inserted_images(
        self,
        document_id: str,
        inserted: Mapping[str, Any],
        image_urls_by_temp_id: Mapping[str, str],
        *,
        document_revision_id: Optional[int],
        client_token: Optional[str],
        user_id_type: Optional[str],
        content_base_dir: str | os.PathLike[str] | None = None,
    ) -> List[Mapping[str, Any]]:
        relations = _extract_relation_map(inserted)
        replacements: List[Mapping[str, Any]] = []
        for temp_block_id, image_url in image_urls_by_temp_id.items():
            block_id = relations.get(temp_block_id)
            if not block_id:
                raise FeishuError(f"docx insert response missing block relation for image block {temp_block_id}")
            downloaded = await _download_binary_async(image_url, base_dir=content_base_dir)
            replacement = await self.replace_image(
                document_id,
                block_id,
                content=downloaded.content,
                file_name=downloaded.file_name,
                content_type=downloaded.content_type,
                document_revision_id=document_revision_id,
                client_token=client_token,
                user_id_type=user_id_type,
            )
            item = {
                "temporary_block_id": temp_block_id,
                "block_id": block_id,
                "image_url": image_url,
                "result": replacement,
            }
            file_token = replacement.get("file_token")
            if isinstance(file_token, str) and file_token:
                item["file_token"] = file_token
            replacements.append(item)
        return replacements

    async def _replace_asset(
        self,
        document_id: str,
        block_id: str,
        *,
        operation_name: str,
        parent_type: str,
        default_file_name: str,
        file_path: Optional[str],
        content: Optional[bytes],
        file_name: Optional[str],
        checksum: Optional[str],
        content_type: Optional[str],
        document_revision_id: Optional[int],
        client_token: Optional[str],
        user_id_type: Optional[str],
    ) -> Mapping[str, Any]:
        if bool(file_path) == bool(content is not None):
            raise ValueError("exactly one of file_path or content is required")

        if file_path is not None:
            upload = await self._drive_files.upload_media(
                file_path,
                parent_type=parent_type,
                parent_node=block_id,
                file_name=file_name,
                checksum=checksum,
                content_type=content_type,
            )
        else:
            upload = await self._drive_files.upload_media_bytes(
                file_name or default_file_name,
                content or b"",
                parent_type=parent_type,
                parent_node=block_id,
                checksum=checksum,
                content_type=content_type,
            )

        file_token = _extract_file_token(upload)
        update = await self._blocks.update_block(
            document_id,
            block_id,
            operations={operation_name: {"token": file_token}},
            document_revision_id=document_revision_id,
            client_token=client_token,
            user_id_type=user_id_type,
        )
        return {
            "document_id": document_id,
            "block_id": block_id,
            "file_token": file_token,
            "upload": upload,
            "update": update,
        }


def _build_document_url(client: FeishuClient | AsyncFeishuClient, document_id: str) -> Optional[str]:
    url_prefix = getattr(client.config, "doc_url_prefix", None)
    if isinstance(url_prefix, str) and url_prefix:
        return url_prefix.rstrip("/") + f"/{document_id}"
    return None


def _extract_document_id(data: Mapping[str, Any]) -> str:
    document = data.get("document")
    if isinstance(document, Mapping):
        document_id = document.get("document_id")
        if isinstance(document_id, str) and document_id:
            return document_id
    document_id = data.get("document_id")
    if isinstance(document_id, str) and document_id:
        return document_id
    raise FeishuError("docx response missing document_id")


def _extract_file_token(data: Mapping[str, Any]) -> str:
    file_token = data.get("file_token")
    if isinstance(file_token, str) and file_token:
        return file_token
    raise FeishuError("drive upload response missing file_token")


def _build_insert_batches(
    converted: Mapping[str, Any],
    *,
    limit: int,
) -> List[_InsertBatch]:
    first_level_block_ids = _extract_string_list(converted.get("first_level_block_ids"))
    blocks = _extract_block_list(converted.get("blocks"))
    image_url_map = _extract_image_url_map(converted.get("block_id_to_image_urls"))
    if not first_level_block_ids or not blocks:
        return []

    block_map = {_extract_block_id(block): block for block in blocks}
    group_batches: List[_InsertBatch] = []
    for root_id in first_level_block_ids:
        subtree_ids = _collect_subtree_ids(root_id, block_map)
        group_blocks: List[Dict[str, Any]] = []
        for block in blocks:
            block_id = _extract_block_id(block)
            if block_id not in subtree_ids:
                continue
            copied = copy.deepcopy(block)
            _strip_table_merge_info(copied)
            group_blocks.append(copied)
        if not group_blocks:
            continue
        group_images = {block_id: url for block_id, url in image_url_map.items() if block_id in subtree_ids}
        group_batches.append(_InsertBatch(root_ids=[root_id], blocks=group_blocks, image_urls=group_images))

    batches: List[_InsertBatch] = []
    current_root_ids: List[str] = []
    current_blocks: List[Dict[str, Any]] = []
    current_image_urls: Dict[str, str] = {}
    for group in group_batches:
        group_size = len(group.blocks)
        if group_size > limit:
            raise FeishuError(f"converted subtree rooted at {group.root_ids[0]} exceeds insert limit {limit}")
        if current_blocks and len(current_blocks) + group_size > limit:
            batches.append(
                _InsertBatch(
                    root_ids=list(current_root_ids),
                    blocks=list(current_blocks),
                    image_urls=dict(current_image_urls),
                )
            )
            current_root_ids = []
            current_blocks = []
            current_image_urls = {}
        current_root_ids.extend(group.root_ids)
        current_blocks.extend(group.blocks)
        current_image_urls.update(group.image_urls)
    if current_blocks:
        batches.append(
            _InsertBatch(
                root_ids=list(current_root_ids),
                blocks=list(current_blocks),
                image_urls=dict(current_image_urls),
            )
        )
    return batches


def _extract_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        if isinstance(item, str) and item:
            result.append(item)
    return result


def _extract_block_list(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: List[Dict[str, Any]] = []
    for item in value:
        if isinstance(item, Mapping):
            normalized = _to_plain_data(item)
            if isinstance(normalized, dict):
                result.append(normalized)
    return result


def _extract_block_id(block: Mapping[str, Any]) -> str:
    block_id = block.get("block_id")
    if isinstance(block_id, str) and block_id:
        return block_id
    raise FeishuError("docx block payload missing block_id")


def _extract_children(block: Mapping[str, Any]) -> List[str]:
    children = block.get("children")
    if not isinstance(children, list):
        return []
    result: List[str] = []
    for item in children:
        if isinstance(item, str) and item:
            result.append(item)
    return result


def _collect_subtree_ids(root_id: str, blocks_by_id: Mapping[str, Mapping[str, Any]]) -> set[str]:
    ids: set[str] = set()
    stack = [root_id]
    while stack:
        block_id = stack.pop()
        if block_id in ids:
            continue
        ids.add(block_id)
        block = blocks_by_id.get(block_id)
        if not isinstance(block, Mapping):
            continue
        stack.extend(_extract_children(block))
    return ids


def _extract_image_url_map(value: Any) -> Dict[str, str]:
    if not isinstance(value, list):
        return {}
    result: Dict[str, str] = {}
    for item in value:
        if not isinstance(item, Mapping):
            continue
        block_id = item.get("block_id")
        image_url = item.get("image_url")
        if isinstance(block_id, str) and block_id and isinstance(image_url, str) and image_url:
            result[block_id] = image_url
    return result


def _extract_relation_map(inserted: Mapping[str, Any]) -> Dict[str, str]:
    relations = inserted.get("block_id_relations")
    if not isinstance(relations, list):
        return {}
    result: Dict[str, str] = {}
    for item in relations:
        if not isinstance(item, Mapping):
            continue
        temporary_block_id = item.get("temporary_block_id")
        block_id = item.get("block_id")
        if isinstance(temporary_block_id, str) and temporary_block_id and isinstance(block_id, str) and block_id:
            result[temporary_block_id] = block_id
    return result


def _strip_table_merge_info(block: Dict[str, Any]) -> None:
    table = block.get("table")
    if not isinstance(table, dict):
        return
    property_data = table.get("property")
    if isinstance(property_data, dict):
        property_data.pop("merge_info", None)


def _download_binary(
    url: str,
    *,
    base_dir: str | os.PathLike[str] | None = None,
) -> _DownloadedAsset:
    local_asset = _read_local_asset(url, base_dir=base_dir)
    if local_asset is not None:
        return local_asset
    normalized_url = _normalize_download_url(url)
    response = httpx.get(normalized_url, timeout=60)
    response.raise_for_status()
    return _DownloadedAsset(
        content=response.content,
        file_name=_guess_file_name(normalized_url, response.headers.get("Content-Type")),
        content_type=response.headers.get("Content-Type"),
    )


async def _download_binary_async(
    url: str,
    *,
    base_dir: str | os.PathLike[str] | None = None,
) -> _DownloadedAsset:
    local_asset = _read_local_asset(url, base_dir=base_dir)
    if local_asset is not None:
        return local_asset
    normalized_url = _normalize_download_url(url)
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(normalized_url)
    response.raise_for_status()
    return _DownloadedAsset(
        content=response.content,
        file_name=_guess_file_name(normalized_url, response.headers.get("Content-Type")),
        content_type=response.headers.get("Content-Type"),
    )


def _normalize_download_url(url: str) -> str:
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _read_local_asset(
    url: str,
    *,
    base_dir: str | os.PathLike[str] | None = None,
) -> _DownloadedAsset | None:
    local_path = _resolve_local_asset_path(url, base_dir=base_dir)
    if local_path is None:
        return None
    if not local_path.is_file():
        raise FeishuError(f"local image file not found: {local_path}")
    content_type, _ = mimetypes.guess_type(local_path.name)
    return _DownloadedAsset(
        content=local_path.read_bytes(),
        file_name=local_path.name or f"asset-{uuid.uuid4().hex}",
        content_type=content_type,
    )


def _resolve_local_asset_path(
    url: str,
    *,
    base_dir: str | os.PathLike[str] | None = None,
) -> Path | None:
    normalized_url = _normalize_download_url(url)
    parsed = urlparse(normalized_url)
    if parsed.scheme in {"http", "https"}:
        return None
    if parsed.scheme and parsed.scheme != "file":
        if len(parsed.scheme) == 1 and normalized_url[1:3] in {":\\", ":/"}:
            return _resolve_local_path(Path(normalized_url), base_dir=base_dir)
        return None

    if parsed.scheme == "file":
        path_text = unquote(parsed.path or "")
        if parsed.netloc and parsed.netloc not in {"", "localhost"}:
            path_text = f"//{parsed.netloc}{path_text}"
        elif path_text.startswith("/") and len(path_text) >= 3 and path_text[2] == ":":
            path_text = path_text[1:]
        return _resolve_local_path(Path(path_text), base_dir=base_dir)

    return _resolve_local_path(Path(normalized_url), base_dir=base_dir)


def _resolve_local_path(
    path: Path,
    *,
    base_dir: str | os.PathLike[str] | None = None,
) -> Path:
    candidate = path.expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    base = Path(base_dir).expanduser() if base_dir is not None else Path.cwd()
    return (base / candidate).resolve(strict=False)


def _guess_file_name(url: str, content_type: Optional[str]) -> str:
    parsed = urlparse(url)
    file_name = os.path.basename(parsed.path)
    if not file_name:
        file_name = f"asset-{uuid.uuid4().hex}"
    _, ext = os.path.splitext(file_name)
    if not ext:
        ext = _content_type_extension(content_type)
        if ext:
            file_name = f"{file_name}{ext}"
    return file_name


def _content_type_extension(content_type: Optional[str]) -> str:
    if not content_type:
        return ""
    mime = content_type.split(";")[0].strip().lower()
    if mime == "image/png":
        return ".png"
    if mime in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if mime == "image/gif":
        return ".gif"
    if mime == "image/webp":
        return ".webp"
    if mime == "application/pdf":
        return ".pdf"
    return ""


def _text_elements(text: str) -> List[Dict[str, Dict[str, str]]]:
    return [{"text_run": {"content": text}}]


def _to_plain_data(value: Any) -> Any:
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _to_plain_data(to_dict())
    if isinstance(value, Mapping):
        return {str(key): _to_plain_data(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [_to_plain_data(item) for item in value]
    return value
