import hashlib
import mimetypes
import os
from typing import Any, Iterator, AsyncIterator, Mapping, Optional, Sequence

import httpx

from ..exceptions import FeishuError, HTTPRequestError
from ..feishu import AsyncFeishuClient, FeishuClient
from ._common import _drop_none, _has_more, _iter_page_files, _next_page_token, _unwrap_data


def _build_file_part(
    filename: str,
    content: bytes,
    content_type: Optional[str],
) -> tuple[str, bytes, str]:
    guessed = content_type or mimetypes.guess_type(filename)[0]
    return (filename, content, guessed or "application/octet-stream")


def _content_sha1(content: bytes) -> str:
    return hashlib.sha1(content).hexdigest()


def _stringify_form_data(form_data: Mapping[str, object]) -> dict[str, str]:
    return {key: str(value) for key, value in form_data.items()}


def _join_file_tokens(file_tokens: Sequence[str]) -> str:
    return ",".join(token for token in file_tokens if token)


class DriveFileService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def batch_query_metas(
        self,
        request_docs: Sequence[Mapping[str, object]],
        *,
        with_url: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"request_docs": [dict(item) for item in request_docs]}
        if with_url is not None:
            payload["with_url"] = with_url
        response = self._client.request_json(
            "POST",
            "/drive/v1/metas/batch_query",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def upload_file(
        self,
        file_path: str,
        *,
        parent_type: str,
        parent_node: str,
        file_name: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        final_name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as file_obj:
            return self.upload_file_bytes(
                final_name,
                file_obj.read(),
                parent_type=parent_type,
                parent_node=parent_node,
                checksum=checksum,
                content_type=content_type,
            )

    def upload_file_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data = {
            "file_name": filename,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        response = self._request_json_raw(
            "POST",
            "/drive/v1/files/upload_all",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    def upload_prepare(
        self,
        *,
        file_name: str,
        parent_type: str,
        parent_node: str,
        size: int,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/drive/v1/files/upload_prepare",
            payload={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": parent_node,
                "size": size,
            },
        )
        return _unwrap_data(response)

    def upload_part(
        self,
        *,
        upload_id: str,
        seq: int,
        content: bytes,
        checksum: Optional[str] = None,
        filename: str = "part.bin",
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data = {
            "upload_id": upload_id,
            "seq": seq,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        response = self._request_json_raw(
            "POST",
            "/drive/v1/files/upload_part",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    def upload_finish(self, *, upload_id: str, block_num: int) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/drive/v1/files/upload_finish",
            payload={"upload_id": upload_id, "block_num": block_num},
        )
        return _unwrap_data(response)

    def download_file(self, file_token: str) -> bytes:
        return self._request_bytes_raw("GET", f"/drive/v1/files/{file_token}/download")

    def get_file_statistics(
        self,
        file_token: str,
        *,
        file_type: str,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/statistics",
            payload={"file_type": file_type},
        )
        return _unwrap_data(response)

    def list_file_view_records(
        self,
        file_token: str,
        *,
        file_type: str,
        page_size: int,
        page_token: Optional[str] = None,
        viewer_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "file_type": file_type,
                "page_size": page_size,
                "page_token": page_token,
                "viewer_id_type": viewer_id_type,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/view_records",
            payload=payload,
        )
        return _unwrap_data(response)

    def copy_file(
        self,
        file_token: str,
        *,
        name: str,
        folder_token: str,
        type: Optional[str] = None,
        extra: Optional[Mapping[str, object]] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload = _drop_none(
            {
                "name": name,
                "type": type,
                "folder_token": folder_token,
                "extra": dict(extra) if extra is not None else None,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/copy",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    def move_file(
        self,
        file_token: str,
        *,
        type: Optional[str] = None,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none({"type": type, "folder_token": folder_token})
        response = self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/move",
            payload=payload,
        )
        return _unwrap_data(response)

    def delete_file(
        self,
        file_token: str,
        *,
        type: str,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/drive/v1/files/{file_token}",
            params={"type": type},
        )
        return _unwrap_data(response)

    def create_shortcut(
        self,
        *,
        parent_token: str,
        refer_token: str,
        refer_type: str,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            "/drive/v1/files/create_shortcut",
            params=params,
            payload={
                "parent_token": parent_token,
                "refer_entity": {
                    "refer_token": refer_token,
                    "refer_type": refer_type,
                },
            },
        )
        return _unwrap_data(response)

    def create_version(
        self,
        file_token: str,
        *,
        name: str,
        obj_type: str,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/versions",
            params=params,
            payload={"name": name, "obj_type": obj_type},
        )
        return _unwrap_data(response)

    def list_versions(
        self,
        file_token: str,
        *,
        obj_type: str,
        page_size: int,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "obj_type": obj_type,
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/drive/v1/files/{file_token}/versions",
            params=params,
        )
        return _unwrap_data(response)

    def get_version(
        self,
        file_token: str,
        version_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/drive/v1/files/{file_token}/versions/{version_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    def delete_version(
        self,
        file_token: str,
        version_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "DELETE",
            f"/drive/v1/files/{file_token}/versions/{version_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    def create_import_task(self, task: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/drive/v1/import_tasks",
            payload=dict(task),
        )
        return _unwrap_data(response)

    def get_import_task(self, ticket: str) -> Mapping[str, Any]:
        response = self._client.request_json("GET", f"/drive/v1/import_tasks/{ticket}")
        return _unwrap_data(response)

    def create_export_task(self, task: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/drive/v1/export_tasks",
            payload=dict(task),
        )
        return _unwrap_data(response)

    def get_export_task(self, ticket: str, *, token: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"token": token})
        response = self._client.request_json(
            "GET",
            f"/drive/v1/export_tasks/{ticket}",
            params=params,
        )
        return _unwrap_data(response)

    def get_task_status(self, task_id: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            "/drive/v1/files/task_check",
            params={"task_id": task_id},
        )
        return _unwrap_data(response)

    def download_export_file(self, file_token: str) -> bytes:
        return self._request_bytes_raw("GET", f"/drive/v1/export_tasks/file/{file_token}/download")

    def upload_media(
        self,
        file_path: str,
        *,
        parent_type: str,
        parent_node: str,
        file_name: Optional[str] = None,
        extra: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        final_name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as file_obj:
            return self.upload_media_bytes(
                final_name,
                file_obj.read(),
                parent_type=parent_type,
                parent_node=parent_node,
                extra=extra,
                checksum=checksum,
                content_type=content_type,
            )

    def upload_media_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        extra: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data: dict[str, object] = {
            "file_name": filename,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        if extra is not None:
            form_data["extra"] = extra
        response = self._request_json_raw(
            "POST",
            "/drive/v1/medias/upload_all",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    def upload_media_prepare(
        self,
        *,
        file_name: str,
        parent_type: str,
        parent_node: str,
        size: int,
        extra: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": size,
        }
        if extra is not None:
            payload["extra"] = extra
        response = self._client.request_json(
            "POST",
            "/drive/v1/medias/upload_prepare",
            payload=payload,
        )
        return _unwrap_data(response)

    def upload_media_part(
        self,
        *,
        upload_id: str,
        seq: int,
        content: bytes,
        checksum: Optional[str] = None,
        filename: str = "part.bin",
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data = {
            "upload_id": upload_id,
            "seq": seq,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        response = self._request_json_raw(
            "POST",
            "/drive/v1/medias/upload_part",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    def upload_media_finish(self, *, upload_id: str, block_num: int) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/drive/v1/medias/upload_finish",
            payload={"upload_id": upload_id, "block_num": block_num},
        )
        return _unwrap_data(response)

    def download_media(self, file_token: str, *, extra: Optional[str] = None) -> bytes:
        params = _drop_none({"extra": extra})
        return self._request_bytes_raw(
            "GET",
            f"/drive/v1/medias/{file_token}/download",
            params=params,
        )

    def batch_get_media_tmp_download_urls(
        self,
        file_tokens: Sequence[str],
        *,
        extra: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"file_tokens": _join_file_tokens(file_tokens), "extra": extra})
        response = self._client.request_json(
            "GET",
            "/drive/v1/medias/batch_get_tmp_download_url",
            params=params,
        )
        return _unwrap_data(response)

    def list_files(
        self,
        *,
        folder_token: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        order_by: Optional[str] = None,
        direction: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({
            "folder_token": folder_token,
            "page_size": page_size,
            "page_token": page_token,
            "order_by": order_by,
            "direction": direction,
            "user_id_type": user_id_type,
        })
        response = self._client.request_json("GET", "/drive/v1/files", params=params)
        return _unwrap_data(response)

    def iter_files(
        self,
        *,
        folder_token: Optional[str] = None,
        page_size: int = 50,
        order_by: Optional[str] = None,
        direction: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_files(
                folder_token=folder_token,
                page_size=page_size,
                page_token=page_token,
                order_by=order_by,
                direction=direction,
                user_id_type=user_id_type,
            )
            yield from _iter_page_files(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_folder(self, *, name: str, folder_token: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            "/drive/v1/files/create_folder",
            payload={"name": name, "folder_token": folder_token},
        )
        return _unwrap_data(response)

    def get_root_folder_meta(self) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            "/drive/explorer/v2/root_folder/meta",
        )
        return _unwrap_data(response)

    def _request_json_raw(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        response = self._request_raw(
            method,
            path,
            form_data=form_data,
            files=files,
            params=params,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise HTTPRequestError("response body is not valid json") from exc
        if not isinstance(payload, Mapping):
            raise HTTPRequestError("response body is not a json object")
        if payload.get("code") != 0:
            raise FeishuError(f"feishu api failed: {payload}")
        return payload

    def _request_bytes_raw(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]] = None,
    ) -> bytes:
        response = self._request_raw(method, path, params=params)
        return response.content

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> httpx.Response:
        token = self._client.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._client.config.base_url}{path}"
        with httpx.Client(timeout=self._client.config.timeout_seconds) as client:
            response = client.request(
                method.upper(),
                url,
                headers=headers,
                params=dict(params or {}),
                data=_stringify_form_data(form_data or {}),
                files=files,
            )
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        return response


class AsyncDriveFileService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def batch_query_metas(
        self,
        request_docs: Sequence[Mapping[str, object]],
        *,
        with_url: Optional[bool] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload: dict[str, object] = {"request_docs": [dict(item) for item in request_docs]}
        if with_url is not None:
            payload["with_url"] = with_url
        response = await self._client.request_json(
            "POST",
            "/drive/v1/metas/batch_query",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def upload_file(
        self,
        file_path: str,
        *,
        parent_type: str,
        parent_node: str,
        file_name: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        final_name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as file_obj:
            return await self.upload_file_bytes(
                final_name,
                file_obj.read(),
                parent_type=parent_type,
                parent_node=parent_node,
                checksum=checksum,
                content_type=content_type,
            )

    async def upload_file_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data = {
            "file_name": filename,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        response = await self._request_json_raw(
            "POST",
            "/drive/v1/files/upload_all",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    async def upload_prepare(
        self,
        *,
        file_name: str,
        parent_type: str,
        parent_node: str,
        size: int,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/drive/v1/files/upload_prepare",
            payload={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": parent_node,
                "size": size,
            },
        )
        return _unwrap_data(response)

    async def upload_part(
        self,
        *,
        upload_id: str,
        seq: int,
        content: bytes,
        checksum: Optional[str] = None,
        filename: str = "part.bin",
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data = {
            "upload_id": upload_id,
            "seq": seq,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        response = await self._request_json_raw(
            "POST",
            "/drive/v1/files/upload_part",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    async def upload_finish(self, *, upload_id: str, block_num: int) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/drive/v1/files/upload_finish",
            payload={"upload_id": upload_id, "block_num": block_num},
        )
        return _unwrap_data(response)

    async def download_file(self, file_token: str) -> bytes:
        return await self._request_bytes_raw("GET", f"/drive/v1/files/{file_token}/download")

    async def get_file_statistics(
        self,
        file_token: str,
        *,
        file_type: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/statistics",
            payload={"file_type": file_type},
        )
        return _unwrap_data(response)

    async def list_file_view_records(
        self,
        file_token: str,
        *,
        file_type: str,
        page_size: int,
        page_token: Optional[str] = None,
        viewer_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "file_type": file_type,
                "page_size": page_size,
                "page_token": page_token,
                "viewer_id_type": viewer_id_type,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/view_records",
            payload=payload,
        )
        return _unwrap_data(response)

    async def copy_file(
        self,
        file_token: str,
        *,
        name: str,
        folder_token: str,
        type: Optional[str] = None,
        extra: Optional[Mapping[str, object]] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        payload = _drop_none(
            {
                "name": name,
                "type": type,
                "folder_token": folder_token,
                "extra": dict(extra) if extra is not None else None,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/copy",
            params=params,
            payload=payload,
        )
        return _unwrap_data(response)

    async def move_file(
        self,
        file_token: str,
        *,
        type: Optional[str] = None,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none({"type": type, "folder_token": folder_token})
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/move",
            payload=payload,
        )
        return _unwrap_data(response)

    async def delete_file(
        self,
        file_token: str,
        *,
        type: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/drive/v1/files/{file_token}",
            params={"type": type},
        )
        return _unwrap_data(response)

    async def create_shortcut(
        self,
        *,
        parent_token: str,
        refer_token: str,
        refer_type: str,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            "/drive/v1/files/create_shortcut",
            params=params,
            payload={
                "parent_token": parent_token,
                "refer_entity": {
                    "refer_token": refer_token,
                    "refer_type": refer_type,
                },
            },
        )
        return _unwrap_data(response)

    async def create_version(
        self,
        file_token: str,
        *,
        name: str,
        obj_type: str,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"user_id_type": user_id_type})
        response = await self._client.request_json(
            "POST",
            f"/drive/v1/files/{file_token}/versions",
            params=params,
            payload={"name": name, "obj_type": obj_type},
        )
        return _unwrap_data(response)

    async def list_versions(
        self,
        file_token: str,
        *,
        obj_type: str,
        page_size: int,
        page_token: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "obj_type": obj_type,
                "page_size": page_size,
                "page_token": page_token,
                "user_id_type": user_id_type,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/drive/v1/files/{file_token}/versions",
            params=params,
        )
        return _unwrap_data(response)

    async def get_version(
        self,
        file_token: str,
        version_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/drive/v1/files/{file_token}/versions/{version_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def delete_version(
        self,
        file_token: str,
        version_id: str,
        *,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "DELETE",
            f"/drive/v1/files/{file_token}/versions/{version_id}",
            params=_drop_none({"user_id_type": user_id_type}),
        )
        return _unwrap_data(response)

    async def create_import_task(self, task: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/drive/v1/import_tasks",
            payload=dict(task),
        )
        return _unwrap_data(response)

    async def get_import_task(self, ticket: str) -> Mapping[str, Any]:
        response = await self._client.request_json("GET", f"/drive/v1/import_tasks/{ticket}")
        return _unwrap_data(response)

    async def create_export_task(self, task: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/drive/v1/export_tasks",
            payload=dict(task),
        )
        return _unwrap_data(response)

    async def get_export_task(self, ticket: str, *, token: Optional[str] = None) -> Mapping[str, Any]:
        params = _drop_none({"token": token})
        response = await self._client.request_json(
            "GET",
            f"/drive/v1/export_tasks/{ticket}",
            params=params,
        )
        return _unwrap_data(response)

    async def get_task_status(self, task_id: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            "/drive/v1/files/task_check",
            params={"task_id": task_id},
        )
        return _unwrap_data(response)

    async def download_export_file(self, file_token: str) -> bytes:
        return await self._request_bytes_raw("GET", f"/drive/v1/export_tasks/file/{file_token}/download")

    async def upload_media(
        self,
        file_path: str,
        *,
        parent_type: str,
        parent_node: str,
        file_name: Optional[str] = None,
        extra: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        final_name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as file_obj:
            return await self.upload_media_bytes(
                final_name,
                file_obj.read(),
                parent_type=parent_type,
                parent_node=parent_node,
                extra=extra,
                checksum=checksum,
                content_type=content_type,
            )

    async def upload_media_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        parent_type: str,
        parent_node: str,
        extra: Optional[str] = None,
        checksum: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data: dict[str, object] = {
            "file_name": filename,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        if extra is not None:
            form_data["extra"] = extra
        response = await self._request_json_raw(
            "POST",
            "/drive/v1/medias/upload_all",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    async def upload_media_prepare(
        self,
        *,
        file_name: str,
        parent_type: str,
        parent_node: str,
        size: int,
        extra: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": size,
        }
        if extra is not None:
            payload["extra"] = extra
        response = await self._client.request_json(
            "POST",
            "/drive/v1/medias/upload_prepare",
            payload=payload,
        )
        return _unwrap_data(response)

    async def upload_media_part(
        self,
        *,
        upload_id: str,
        seq: int,
        content: bytes,
        checksum: Optional[str] = None,
        filename: str = "part.bin",
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data = {
            "upload_id": upload_id,
            "seq": seq,
            "size": len(content),
        }
        if checksum is not None:
            form_data["checksum"] = checksum
        response = await self._request_json_raw(
            "POST",
            "/drive/v1/medias/upload_part",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    async def upload_media_finish(self, *, upload_id: str, block_num: int) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/drive/v1/medias/upload_finish",
            payload={"upload_id": upload_id, "block_num": block_num},
        )
        return _unwrap_data(response)

    async def download_media(self, file_token: str, *, extra: Optional[str] = None) -> bytes:
        params = _drop_none({"extra": extra})
        return await self._request_bytes_raw(
            "GET",
            f"/drive/v1/medias/{file_token}/download",
            params=params,
        )

    async def batch_get_media_tmp_download_urls(
        self,
        file_tokens: Sequence[str],
        *,
        extra: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"file_tokens": _join_file_tokens(file_tokens), "extra": extra})
        response = await self._client.request_json(
            "GET",
            "/drive/v1/medias/batch_get_tmp_download_url",
            params=params,
        )
        return _unwrap_data(response)

    async def list_files(
        self,
        *,
        folder_token: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        order_by: Optional[str] = None,
        direction: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({
            "folder_token": folder_token,
            "page_size": page_size,
            "page_token": page_token,
            "order_by": order_by,
            "direction": direction,
            "user_id_type": user_id_type,
        })
        response = await self._client.request_json("GET", "/drive/v1/files", params=params)
        return _unwrap_data(response)

    async def iter_files(
        self,
        *,
        folder_token: Optional[str] = None,
        page_size: int = 50,
        order_by: Optional[str] = None,
        direction: Optional[str] = None,
        user_id_type: Optional[str] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_files(
                folder_token=folder_token,
                page_size=page_size,
                page_token=page_token,
                order_by=order_by,
                direction=direction,
                user_id_type=user_id_type,
            )
            for item in _iter_page_files(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def create_folder(self, *, name: str, folder_token: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            "/drive/v1/files/create_folder",
            payload={"name": name, "folder_token": folder_token},
        )
        return _unwrap_data(response)

    async def get_root_folder_meta(self) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            "/drive/explorer/v2/root_folder/meta",
        )
        return _unwrap_data(response)

    async def _request_json_raw(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        response = await self._request_raw(
            method,
            path,
            form_data=form_data,
            files=files,
            params=params,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise HTTPRequestError("response body is not valid json") from exc
        if not isinstance(payload, Mapping):
            raise HTTPRequestError("response body is not a json object")
        if payload.get("code") != 0:
            raise FeishuError(f"feishu api failed: {payload}")
        return payload

    async def _request_bytes_raw(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]] = None,
    ) -> bytes:
        response = await self._request_raw(method, path, params=params)
        return response.content

    async def _request_raw(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, object]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, object]] = None,
    ) -> httpx.Response:
        token = await self._client.get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._client.config.base_url}{path}"
        async with httpx.AsyncClient(timeout=self._client.config.timeout_seconds) as client:
            response = await client.request(
                method.upper(),
                url,
                headers=headers,
                params=dict(params or {}),
                data=_stringify_form_data(form_data or {}),
                files=files,
            )
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
                response_headers=dict(response.headers),
            )
        return response
