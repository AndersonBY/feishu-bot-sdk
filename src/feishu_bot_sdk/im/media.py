import mimetypes
import os
from typing import Any, Mapping, Optional

import httpx

from ..exceptions import FeishuError, HTTPRequestError
from ..feishu import AsyncFeishuClient, FeishuClient


class MediaService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def upload_image(
        self,
        image_path: str,
        *,
        image_type: str = "message",
    ) -> Mapping[str, Any]:
        filename = os.path.basename(image_path)
        with open(image_path, "rb") as image_file:
            return self.upload_image_bytes(
                filename,
                image_file.read(),
                image_type=image_type,
            )

    def upload_image_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        image_type: str = "message",
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = self._request_json(
            "POST",
            "/im/v1/images",
            form_data={"image_type": image_type},
            files={"image": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    def download_image(self, image_key: str) -> bytes:
        return self._request_bytes("GET", f"/im/v1/images/{image_key}")

    def upload_file(
        self,
        file_path: str,
        *,
        file_type: str = "stream",
        file_name: Optional[str] = None,
        duration: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        final_name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as file_obj:
            return self.upload_file_bytes(
                final_name,
                file_obj.read(),
                file_type=file_type,
                duration=duration,
                content_type=content_type,
            )

    def upload_file_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        file_type: str = "stream",
        duration: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data: dict[str, str] = {
            "file_type": file_type,
            "file_name": filename,
        }
        if duration is not None:
            form_data["duration"] = str(duration)

        response = self._request_json(
            "POST",
            "/im/v1/files",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    def download_file(self, file_key: str) -> bytes:
        return self._request_bytes("GET", f"/im/v1/files/{file_key}")

    def download_message_resource(
        self,
        message_id: str,
        file_key: str,
        *,
        resource_type: str,
    ) -> bytes:
        return self._request_bytes(
            "GET",
            f"/im/v1/messages/{message_id}/resources/{file_key}",
            params={"type": resource_type},
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
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
        if not isinstance(payload, dict):
            raise HTTPRequestError("response body is not a json object")
        if payload.get("code") != 0:
            raise FeishuError(f"feishu api failed: {payload}")
        return payload

    def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, str]] = None,
    ) -> bytes:
        response = self._request_raw(method, path, params=params)
        return response.content

    def _request_raw(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
    ) -> httpx.Response:
        token = self._client.get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._client.config.base_url}{path}"
        with httpx.Client(timeout=self._client.config.timeout_seconds) as client:
            response = client.request(
                method.upper(),
                url,
                headers=headers,
                params=dict(params or {}),
                data=dict(form_data or {}),
                files=files,
            )
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
            )
        return response


class AsyncMediaService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def upload_image(
        self,
        image_path: str,
        *,
        image_type: str = "message",
    ) -> Mapping[str, Any]:
        filename = os.path.basename(image_path)
        with open(image_path, "rb") as image_file:
            return await self.upload_image_bytes(
                filename,
                image_file.read(),
                image_type=image_type,
            )

    async def upload_image_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        image_type: str = "message",
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        response = await self._request_json(
            "POST",
            "/im/v1/images",
            form_data={"image_type": image_type},
            files={"image": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    async def download_image(self, image_key: str) -> bytes:
        return await self._request_bytes("GET", f"/im/v1/images/{image_key}")

    async def upload_file(
        self,
        file_path: str,
        *,
        file_type: str = "stream",
        file_name: Optional[str] = None,
        duration: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        final_name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as file_obj:
            return await self.upload_file_bytes(
                final_name,
                file_obj.read(),
                file_type=file_type,
                duration=duration,
                content_type=content_type,
            )

    async def upload_file_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        file_type: str = "stream",
        duration: Optional[int] = None,
        content_type: Optional[str] = None,
    ) -> Mapping[str, Any]:
        form_data: dict[str, str] = {
            "file_type": file_type,
            "file_name": filename,
        }
        if duration is not None:
            form_data["duration"] = str(duration)

        response = await self._request_json(
            "POST",
            "/im/v1/files",
            form_data=form_data,
            files={"file": _build_file_part(filename, content, content_type)},
        )
        return _unwrap_data(response)

    async def download_file(self, file_key: str) -> bytes:
        return await self._request_bytes("GET", f"/im/v1/files/{file_key}")

    async def download_message_resource(
        self,
        message_id: str,
        file_key: str,
        *,
        resource_type: str,
    ) -> bytes:
        return await self._request_bytes(
            "GET",
            f"/im/v1/messages/{message_id}/resources/{file_key}",
            params={"type": resource_type},
        )

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
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
        if not isinstance(payload, dict):
            raise HTTPRequestError("response body is not a json object")
        if payload.get("code") != 0:
            raise FeishuError(f"feishu api failed: {payload}")
        return payload

    async def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, str]] = None,
    ) -> bytes:
        response = await self._request_raw(method, path, params=params)
        return response.content

    async def _request_raw(
        self,
        method: str,
        path: str,
        *,
        form_data: Optional[Mapping[str, str]] = None,
        files: Optional[Mapping[str, Any]] = None,
        params: Optional[Mapping[str, str]] = None,
    ) -> httpx.Response:
        token = await self._client.get_tenant_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self._client.config.base_url}{path}"
        async with httpx.AsyncClient(timeout=self._client.config.timeout_seconds) as client:
            response = await client.request(
                method.upper(),
                url,
                headers=headers,
                params=dict(params or {}),
                data=dict(form_data or {}),
                files=files,
            )
        if response.status_code >= 400:
            raise HTTPRequestError(
                f"http request failed: {response.status_code}",
                status_code=response.status_code,
                response_text=response.text,
            )
        return response


def _build_file_part(
    filename: str,
    content: bytes,
    content_type: Optional[str],
) -> tuple[str, bytes, str]:
    guessed = content_type or mimetypes.guess_type(filename)[0]
    return (filename, content, guessed or "application/octet-stream")


def _unwrap_data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return data
    return {}
