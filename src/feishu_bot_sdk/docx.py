import os
import re
import uuid
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, cast
from urllib.parse import urlparse

import httpx

from .drive_acl import AsyncDrivePermissionService, DrivePermissionService
from .exceptions import FeishuError
from .feishu import AsyncFeishuClient, FeishuClient
from .types import DriveResourceType, MemberIdType


_BLOCK_BATCH_SIZE = 200


@dataclass(frozen=True)
class _ImageSpec:
    temp_block_id: str
    url: str
    alt_text: str


@dataclass
class _BlockGroup:
    root_ids: List[str]
    blocks: List[Dict[str, object]]
    images: List[_ImageSpec]


_IMAGE_PATTERN = re.compile(r"^\s*!\[(.*?)\]\((\S+?)(?:\s+\"(.*?)\")?\)\s*$")
_INLINE_IMAGE_RE = re.compile(r"!\[(.*?)\]\((\S+?)(?:\s+\"(.*?)\")?\)")
_TABLE_SEPARATOR_RE = re.compile(r"^:?-+:?$")


class DocxService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client
        self._drive_permissions = DrivePermissionService(feishu_client)

    def create_document(self, title: str) -> Tuple[str, Optional[str]]:
        payload: Dict[str, str] = {"title": title}
        if self._client.config.doc_folder_token:
            payload["folder_token"] = self._client.config.doc_folder_token
        resp = self._client.request_json("POST", "/docx/v1/documents", payload=payload)
        document_id = resp["data"]["document"]["document_id"]
        url_prefix = self._client.config.doc_url_prefix
        if url_prefix:
            return document_id, url_prefix.rstrip("/") + f"/{document_id}"
        return document_id, None

    def append_markdown(self, document_id: str, markdown_text: str) -> None:
        groups = _markdown_to_groups(markdown_text)
        if not groups:
            groups = [_text_group(" ")]
        for batch in _chunked_groups(groups, _BLOCK_BATCH_SIZE):
            descendants: List[Dict[str, object]] = []
            children_id: List[str] = []
            images_by_temp: Dict[str, _ImageSpec] = {}
            for group in batch:
                descendants.extend(group.blocks)
                children_id.extend(group.root_ids)
                for image in group.images:
                    images_by_temp[image.temp_block_id] = image
            payload = {
                "index": -1,
                "children_id": children_id,
                "descendants": descendants,
            }
            resp = self._client.request_json(
                "POST",
                f"/docx/v1/documents/{document_id}/blocks/{document_id}/descendant",
                payload=payload,
                params={"document_revision_id": -1},
            )
            if images_by_temp:
                relations = resp.get("data", {}).get("block_id_relations", [])
                _replace_images(
                    self._client,
                    document_id,
                    relations,
                    images_by_temp,
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


class AsyncDocxService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client
        self._drive_permissions = AsyncDrivePermissionService(feishu_client)

    async def create_document(self, title: str) -> Tuple[str, Optional[str]]:
        payload: Dict[str, str] = {"title": title}
        if self._client.config.doc_folder_token:
            payload["folder_token"] = self._client.config.doc_folder_token
        resp = await self._client.request_json("POST", "/docx/v1/documents", payload=payload)
        document_id = resp["data"]["document"]["document_id"]
        url_prefix = self._client.config.doc_url_prefix
        if url_prefix:
            return document_id, url_prefix.rstrip("/") + f"/{document_id}"
        return document_id, None

    async def append_markdown(self, document_id: str, markdown_text: str) -> None:
        groups = _markdown_to_groups(markdown_text)
        if not groups:
            groups = [_text_group(" ")]
        for batch in _chunked_groups(groups, _BLOCK_BATCH_SIZE):
            descendants: List[Dict[str, object]] = []
            children_id: List[str] = []
            images_by_temp: Dict[str, _ImageSpec] = {}
            for group in batch:
                descendants.extend(group.blocks)
                children_id.extend(group.root_ids)
                for image in group.images:
                    images_by_temp[image.temp_block_id] = image
            payload = {
                "index": -1,
                "children_id": children_id,
                "descendants": descendants,
            }
            resp = await self._client.request_json(
                "POST",
                f"/docx/v1/documents/{document_id}/blocks/{document_id}/descendant",
                payload=payload,
                params={"document_revision_id": -1},
            )
            if images_by_temp:
                relations = resp.get("data", {}).get("block_id_relations", [])
                await _replace_images_async(
                    self._client,
                    document_id,
                    relations,
                    images_by_temp,
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


def _markdown_to_groups(markdown_text: str) -> List[_BlockGroup]:
    groups: List[_BlockGroup] = []
    in_code = False
    code_lang: Optional[str] = None
    code_lines: List[str] = []
    para_lines: List[str] = []

    def flush_paragraph() -> None:
        if not para_lines:
            return
        text = " ".join(part.strip() for part in para_lines).strip()
        if text:
            groups.append(_text_group(text))
        para_lines.clear()

    lines = markdown_text.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].rstrip("\n")
        fence_match = re.match(r"^```(.*)$", line.strip())
        if fence_match:
            if in_code:
                groups.append(_code_group("\n".join(code_lines), code_lang))
                in_code = False
                code_lang = None
                code_lines = []
            else:
                flush_paragraph()
                in_code = True
                lang = fence_match.group(1).strip()
                code_lang = lang or None
            idx += 1
            continue

        if in_code:
            code_lines.append(line)
            idx += 1
            continue

        table_group, next_idx = _parse_table(lines, idx)
        if table_group:
            flush_paragraph()
            groups.append(table_group)
            idx = next_idx
            continue

        list_group, next_idx = _parse_list(lines, idx)
        if list_group:
            flush_paragraph()
            groups.append(list_group)
            idx = next_idx
            continue

        image_match = _IMAGE_PATTERN.match(line)
        if image_match:
            flush_paragraph()
            alt_text = (image_match.group(1) or "").strip()
            url = (image_match.group(2) or "").strip()
            if url:
                groups.append(_image_group(url, alt_text))
            idx += 1
            continue

        if not line.strip():
            flush_paragraph()
            idx += 1
            continue

        heading_match = re.match(r"^(#{1,9})\s+(.*)$", line)
        if heading_match:
            flush_paragraph()
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            if text:
                groups.append(_heading_group(level, text))
            idx += 1
            continue

        quote_match = re.match(r"^>\s?(.*)$", line)
        if quote_match:
            flush_paragraph()
            groups.append(_quote_group(quote_match.group(1).strip()))
            idx += 1
            continue

        para_lines.append(line.strip())
        idx += 1

    if in_code:
        groups.append(_code_group("\n".join(code_lines), code_lang))
    flush_paragraph()
    return groups


def _text_group(text: str) -> _BlockGroup:
    block = _text_block(text)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[])


def _heading_group(level: int, text: str) -> _BlockGroup:
    block = _heading_block(level, text)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[])


def _bullet_group(text: str) -> _BlockGroup:
    block = _bullet_block(text)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[])


def _ordered_group(text: str) -> _BlockGroup:
    block = _ordered_block(text)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[])


def _quote_group(text: str) -> _BlockGroup:
    block = _quote_block(text)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[])


def _code_group(text: str, language: Optional[str]) -> _BlockGroup:
    block = _code_block(text, language)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[])


def _image_group(url: str, alt_text: str) -> _BlockGroup:
    block, image = _image_block(url, alt_text)
    block_id = _get_block_id(block)
    return _BlockGroup(root_ids=[block_id], blocks=[block], images=[image])


def _parse_table(lines: List[str], start_index: int) -> Tuple[Optional[_BlockGroup], int]:
    if start_index + 1 >= len(lines):
        return None, start_index
    header_line = lines[start_index].rstrip("\n")
    divider_line = lines[start_index + 1].rstrip("\n")
    if "|" not in header_line or not _is_table_separator(divider_line):
        return None, start_index
    header_cells = _split_table_row(header_line)
    divider_cells = _split_table_row(divider_line)
    if not header_cells or len(divider_cells) < len(header_cells):
        return None, start_index
    rows: List[List[str]] = []
    idx = start_index + 2
    while idx < len(lines):
        row_line = lines[idx].rstrip("\n")
        if not row_line.strip() or "|" not in row_line or _is_table_separator(row_line):
            break
        rows.append(_split_table_row(row_line))
        idx += 1
    return _table_group(header_cells, rows), idx


def _parse_list(lines: List[str], start_index: int) -> Tuple[Optional[_BlockGroup], int]:
    items: List[Tuple[int, str, str]] = []
    idx = start_index
    while idx < len(lines):
        line = lines[idx].rstrip("\n")
        if not line.strip():
            break
        parsed = _parse_list_item_line(line)
        if not parsed:
            break
        items.append(parsed)
        idx += 1
    if not items:
        return None, start_index
    return _list_group(items), idx


def _parse_list_item_line(line: str) -> Optional[Tuple[int, str, str]]:
    bullet_match = re.match(r"^(\s*)([-*+])\s+(.*)$", line)
    if bullet_match:
        indent = _indent_level(bullet_match.group(1))
        return indent, "bullet", bullet_match.group(3).strip()
    ordered_match = re.match(r"^(\s*)(\d+)\.\s+(.*)$", line)
    if ordered_match:
        indent = _indent_level(ordered_match.group(1))
        return indent, "ordered", ordered_match.group(3).strip()
    return None


def _indent_level(indent: str) -> int:
    spaces = 0
    for ch in indent:
        spaces += 4 if ch == "\t" else 1
    if spaces >= 4:
        return spaces // 4
    return spaces // 2


def _list_group(items: List[Tuple[int, str, str]]) -> _BlockGroup:
    blocks: List[Dict[str, object]] = []
    images: List[_ImageSpec] = []
    root_ids: List[str] = []
    block_by_id: Dict[str, Dict[str, object]] = {}
    stack: List[Tuple[int, str]] = []

    for indent_level, list_type, content in items:
        cleaned, inline_images = _extract_inline_images(content)
        text_content = cleaned.strip() or " "
        if list_type == "ordered":
            block = _ordered_block(text_content)
        else:
            block = _bullet_block(text_content)
        block_id = _get_block_id(block)
        children: List[str] = []
        block["children"] = children
        block_by_id[block_id] = block
        blocks.append(block)

        for url, alt_text in inline_images:
            image_block, image_spec = _image_block(url, alt_text)
            children.append(_get_block_id(image_block))
            blocks.append(image_block)
            images.append(image_spec)

        while stack and stack[-1][0] >= indent_level:
            stack.pop()
        if stack:
            parent_id = stack[-1][1]
            parent_block = block_by_id[parent_id]
            parent_children = parent_block.setdefault("children", [])
            cast(List[str], parent_children).append(block_id)
        else:
            root_ids.append(block_id)
        stack.append((indent_level, block_id))

    return _BlockGroup(root_ids=root_ids, blocks=blocks, images=images)


def _extract_inline_images(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    images: List[Tuple[str, str]] = []
    parts: List[str] = []
    last = 0
    for match in _INLINE_IMAGE_RE.finditer(text):
        parts.append(text[last : match.start()])
        alt_text = (match.group(1) or "").strip()
        url = (match.group(2) or "").strip()
        if url:
            images.append((url, alt_text))
        last = match.end()
    parts.append(text[last:])
    cleaned = "".join(parts)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned, images


def _image_block(url: str, alt_text: str) -> Tuple[Dict[str, object], _ImageSpec]:
    block_id = _new_block_id()
    image_payload: Dict[str, object] = {}
    if alt_text:
        image_payload["caption"] = {"content": alt_text}
    block = {
        "block_id": block_id,
        "block_type": 27,
        "image": image_payload,
        "children": [],
    }
    image = _ImageSpec(temp_block_id=block_id, url=url, alt_text=alt_text)
    return block, image


def _split_table_row(line: str) -> List[str]:
    parts = re.split(r"(?<!\\)\|", line)
    if parts and not parts[0].strip():
        parts = parts[1:]
    if parts and not parts[-1].strip():
        parts = parts[:-1]
    cleaned = []
    for part in parts:
        text = part.replace("\\|", "|").replace("\\\\", "\\").strip()
        cleaned.append(text)
    return cleaned


def _is_table_separator(line: str) -> bool:
    if "|" not in line:
        return False
    cells = _split_table_row(line)
    if not cells:
        return False
    return all(_TABLE_SEPARATOR_RE.match(cell.strip() or "-") for cell in cells)


def _table_group(header_cells: List[str], rows: List[List[str]]) -> _BlockGroup:
    all_rows = [header_cells] + rows
    row_size = len(all_rows)
    column_size = max((len(row) for row in all_rows), default=0)
    if column_size == 0:
        return _text_group(" ")
    column_widths: List[int] = []
    for col_idx in range(column_size):
        max_len = 0
        for row in all_rows:
            if col_idx < len(row):
                max_len = max(max_len, len(row[col_idx]))
        width = max(160, min(360, max_len * 14))
        column_widths.append(width)
    cell_ids: List[str] = []
    blocks: List[Dict[str, object]] = []
    for row in all_rows:
        padded = row + [""] * (column_size - len(row))
        for cell_text in padded:
            text_block = _text_block(cell_text)
            cell_block_id = _new_block_id()
            cell_block = {
                "block_id": cell_block_id,
                "block_type": 32,
                "table_cell": {},
                "children": [text_block["block_id"]],
            }
            blocks.append(cell_block)
            blocks.append(text_block)
            cell_ids.append(cell_block_id)
    table_id = _new_block_id()
    table_block = {
        "block_id": table_id,
        "block_type": 31,
        "table": {
            "property": {
                "row_size": row_size,
                "column_size": column_size,
                "column_width": column_widths,
                "header_row": True,
            }
        },
        "children": cell_ids,
    }
    blocks.insert(0, table_block)
    return _BlockGroup(root_ids=[table_id], blocks=blocks, images=[])


def _get_block_id(block: Dict[str, object]) -> str:
    return cast(str, block["block_id"])


def _replace_images(
    client: FeishuClient,
    document_id: str,
    relations: List[Dict[str, str]],
    images_by_temp: Dict[str, _ImageSpec],
) -> None:
    for relation in relations:
        temp_id = relation.get("temporary_block_id")
        block_id = relation.get("block_id")
        if not temp_id or not block_id:
            continue
        image_spec = images_by_temp.get(temp_id)
        if not image_spec:
            continue
        image_bytes, file_name = _download_image(image_spec.url)
        file_token = _upload_docx_image(client, block_id, image_bytes, file_name)
        _replace_image_block(client, document_id, block_id, file_token)


async def _replace_images_async(
    client: AsyncFeishuClient,
    document_id: str,
    relations: List[Dict[str, str]],
    images_by_temp: Dict[str, _ImageSpec],
) -> None:
    for relation in relations:
        temp_id = relation.get("temporary_block_id")
        block_id = relation.get("block_id")
        if not temp_id or not block_id:
            continue
        image_spec = images_by_temp.get(temp_id)
        if not image_spec:
            continue
        image_bytes, file_name = await _download_image_async(image_spec.url)
        file_token = await _upload_docx_image_async(client, block_id, image_bytes, file_name)
        await _replace_image_block_async(client, document_id, block_id, file_token)


def _download_image(url: str) -> Tuple[bytes, str]:
    resp = httpx.get(url, timeout=60)
    resp.raise_for_status()
    file_name = _image_file_name(url, resp.headers.get("Content-Type"))
    return resp.content, file_name


async def _download_image_async(url: str) -> Tuple[bytes, str]:
    async with httpx.AsyncClient(timeout=60) as async_client:
        resp = await async_client.get(url)
    resp.raise_for_status()
    file_name = _image_file_name(url, resp.headers.get("Content-Type"))
    return resp.content, file_name


def _image_file_name(url: str, content_type: Optional[str]) -> str:
    parsed = urlparse(url)
    base_name = os.path.basename(parsed.path)
    if not base_name:
        base_name = f"image-{uuid.uuid4().hex}"
    _, ext = os.path.splitext(base_name)
    if not ext:
        ext = _content_type_extension(content_type)
        if ext:
            base_name = f"{base_name}{ext}"
    return base_name


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
    return ""


def _upload_docx_image(
    client: FeishuClient,
    image_block_id: str,
    image_bytes: bytes,
    file_name: str,
) -> str:
    token = client.get_tenant_access_token()
    url = f"{client.config.base_url}/drive/v1/medias/upload_all"
    data = {
        "file_name": file_name,
        "parent_type": "docx_image",
        "parent_node": image_block_id,
        "size": str(len(image_bytes)),
    }
    files = {"file": (file_name, image_bytes)}
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
        timeout=60,
    )
    if resp.status_code >= 400:
        raise FeishuError(f"Feishu image upload failed: {resp.status_code} {resp.text}")
    payload = resp.json()
    if payload.get("code") != 0:
        raise FeishuError(f"feishu image upload failed: {payload}")
    return payload["data"]["file_token"]


async def _upload_docx_image_async(
    client: AsyncFeishuClient,
    image_block_id: str,
    image_bytes: bytes,
    file_name: str,
) -> str:
    token = await client.get_tenant_access_token()
    url = f"{client.config.base_url}/drive/v1/medias/upload_all"
    data = {
        "file_name": file_name,
        "parent_type": "docx_image",
        "parent_node": image_block_id,
        "size": str(len(image_bytes)),
    }
    files = {"file": (file_name, image_bytes)}
    async with httpx.AsyncClient(timeout=60) as async_client:
        resp = await async_client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            data=data,
            files=files,
        )
    if resp.status_code >= 400:
        raise FeishuError(f"Feishu image upload failed: {resp.status_code} {resp.text}")
    payload = resp.json()
    if payload.get("code") != 0:
        raise FeishuError(f"feishu image upload failed: {payload}")
    return payload["data"]["file_token"]


def _replace_image_block(
    client: FeishuClient,
    document_id: str,
    block_id: str,
    file_token: str,
) -> None:
    payload = {"replace_image": {"token": file_token}}
    client.request_json(
        "PATCH",
        f"/docx/v1/documents/{document_id}/blocks/{block_id}",
        payload=payload,
    )


async def _replace_image_block_async(
    client: AsyncFeishuClient,
    document_id: str,
    block_id: str,
    file_token: str,
) -> None:
    payload = {"replace_image": {"token": file_token}}
    await client.request_json(
        "PATCH",
        f"/docx/v1/documents/{document_id}/blocks/{block_id}",
        payload=payload,
    )


def _text_elements(text: str, parse_inline: bool = False) -> List[Dict[str, Dict[str, object]]]:
    if not parse_inline:
        return [{"text_run": {"content": text}}]
    elements: List[Dict[str, Dict[str, object]]] = []
    buffer: List[str] = []

    def flush_plain() -> None:
        if not buffer:
            return
        content = "".join(buffer)
        elements.append({"text_run": {"content": content}})
        buffer.clear()

    def append_run(content: str, style: Dict[str, bool]) -> None:
        if not content:
            return
        run: Dict[str, object] = {"content": content, "text_element_style": style}
        elements.append({"text_run": run})

    idx = 0
    while idx < len(text):
        ch = text[idx]
        if ch == "\\" and idx + 1 < len(text):
            buffer.append(text[idx + 1])
            idx += 2
            continue
        if text.startswith("**", idx) or text.startswith("__", idx):
            delim = text[idx : idx + 2]
            end = text.find(delim, idx + 2)
            if end != -1:
                flush_plain()
                append_run(text[idx + 2 : end], {"bold": True})
                idx = end + 2
                continue
        if ch == "`":
            end = text.find("`", idx + 1)
            if end != -1:
                flush_plain()
                append_run(text[idx + 1 : end], {"inline_code": True})
                idx = end + 1
                continue
        buffer.append(ch)
        idx += 1

    flush_plain()
    if not elements:
        return [{"text_run": {"content": ""}}]
    return elements


def _new_block_id() -> str:
    return uuid.uuid4().hex


def _text_block(text: str, parse_inline: bool = True) -> Dict[str, object]:
    return {
        "block_id": _new_block_id(),
        "block_type": 2,
        "text": {"elements": _text_elements(text, parse_inline=parse_inline)},
        "children": [],
    }


def _heading_block(level: int, text: str) -> Dict[str, object]:
    level = max(1, min(level, 9))
    block_type = 2 + level
    key = f"heading{level}"
    return {
        "block_id": _new_block_id(),
        "block_type": block_type,
        key: {"elements": _text_elements(text, parse_inline=True)},
        "children": [],
    }


def _bullet_block(text: str) -> Dict[str, object]:
    return {
        "block_id": _new_block_id(),
        "block_type": 12,
        "bullet": {"elements": _text_elements(text, parse_inline=True)},
        "children": [],
    }


def _ordered_block(text: str) -> Dict[str, object]:
    return {
        "block_id": _new_block_id(),
        "block_type": 13,
        "ordered": {"elements": _text_elements(text, parse_inline=True)},
        "children": [],
    }


def _quote_block(text: str) -> Dict[str, object]:
    return {
        "block_id": _new_block_id(),
        "block_type": 15,
        "quote": {"elements": _text_elements(text, parse_inline=True)},
        "children": [],
    }


def _code_block(text: str, _language: Optional[str]) -> Dict[str, object]:
    return {
        "block_id": _new_block_id(),
        "block_type": 14,
        "code": {"elements": _text_elements(text, parse_inline=False), "language": 1, "wrap": True},
        "children": [],
    }


def _chunked_groups(
    groups: List[_BlockGroup], size: int
) -> Iterable[List[_BlockGroup]]:
    batch: List[_BlockGroup] = []
    count = 0
    for group in groups:
        group_size = len(group.blocks)
        if batch and count + group_size > size:
            yield batch
            batch = []
            count = 0
        batch.append(group)
        count += group_size
    if batch:
        yield batch
