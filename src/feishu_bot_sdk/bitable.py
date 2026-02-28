import csv
import os
from typing import Any, AsyncIterator, Dict, Iterable, Iterator, List, Mapping, Optional, Set

from .drive_acl import AsyncDrivePermissionService, DrivePermissionService
from .feishu import AsyncFeishuClient, FeishuClient
from .types import DriveResourceType, MemberIdType


INVALID_FIELD_CHARS = {"/", "\\", "?", "*", ":", "[", "]"}


def _is_http_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _sanitize_field_name(name: str, fallback: str) -> str:
    cleaned = "".join(ch for ch in name.strip() if ch not in INVALID_FIELD_CHARS)
    if not cleaned:
        cleaned = fallback
    return cleaned[:100]


def _unique_names(names: List[str]) -> List[str]:
    used = set()
    unique = []
    for name in names:
        base = name
        candidate = base
        index = 1
        while candidate in used:
            index += 1
            candidate = f"{base}_{index}"
        used.add(candidate)
        unique.append(candidate[:100])
    return unique


def _prepare_headers(raw_headers: List[str]) -> List[str]:
    sanitized = [_sanitize_field_name(h, f"Column{i + 1}") for i, h in enumerate(raw_headers)]
    return _unique_names(sanitized)


def _iter_csv_rows(
    csv_path: str,
    base_headers: List[str],
    url_indices: Set[int],
) -> Iterable[Dict[str, object]]:
    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        _ = next(reader, None)
        for row in reader:
            if len(row) < len(base_headers):
                row = row + [""] * (len(base_headers) - len(row))
            if len(row) > len(base_headers):
                row = row[: len(base_headers)]

            record: Dict[str, object] = {}
            for index, header in enumerate(base_headers):
                value = row[index]
                if index in url_indices:
                    url_value = value.strip()
                    if _is_http_url(url_value):
                        record[header] = {"text": url_value, "link": url_value}
                    else:
                        continue
                else:
                    record[header] = value
            yield record


def _chunked(items: Iterable[Dict[str, object]], size: int) -> Iterable[List[Dict[str, object]]]:
    batch: List[Dict[str, object]] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _detect_url_indices(csv_path: str, header_count: int) -> Set[int]:
    url_indices: Set[int] = set()
    with open(csv_path, newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        _ = next(reader, None)
        for row in reader:
            if len(url_indices) == header_count:
                break
            limit = min(len(row), header_count)
            for index in range(limit):
                if index in url_indices:
                    continue
                value = row[index].strip()
                if _is_http_url(value):
                    url_indices.add(index)
            if len(url_indices) == header_count:
                break
    return url_indices


def _drop_none(params: Mapping[str, object]) -> Dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> Mapping[str, Any]:
    data = response.get("data")
    if isinstance(data, Mapping):
        return data
    return {}


def _iter_page_items(data: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
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


class BitableService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client
        self._drive_permissions = DrivePermissionService(feishu_client)

    def create_from_csv(self, csv_path: str, app_name: str, table_name: str) -> tuple[str, str]:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(csv_path)

        with open(csv_path, newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            raw_headers = next(reader, [])

        headers = _prepare_headers(raw_headers)
        url_indices = _detect_url_indices(csv_path, len(headers))

        app_resp = self._client.request_json("POST", "/bitable/v1/apps", payload={"name": app_name})
        app_token = app_resp["data"]["app"]["app_token"]
        app_url = app_resp["data"]["app"]["url"]

        fields = []
        for index, name in enumerate(headers):
            if index in url_indices:
                fields.append({"field_name": name, "type": 15, "ui_type": "Url"})
            else:
                fields.append({"field_name": name, "type": 1})
        table_payload: Dict[str, Dict[str, object]] = {"table": {"name": table_name}}
        if fields:
            table_payload["table"]["default_view_name"] = "Grid"
            table_payload["table"]["fields"] = fields
        table_resp = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables",
            payload=table_payload,
        )
        table_id = table_resp["data"]["table_id"]

        self._cleanup_default_tables(app_token, table_id)

        rows = _iter_csv_rows(csv_path, headers, url_indices)
        for batch in _chunked(rows, 1000):
            self._client.request_json(
                "POST",
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
                payload={"records": [{"fields": row} for row in batch]},
            )
        return app_token, app_url

    def grant_edit_permission(
        self,
        app_token: str,
        member_id: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
    ) -> None:
        self._drive_permissions.grant_edit_permission(
            app_token,
            member_id,
            member_id_type,
            resource_type=DriveResourceType.BITABLE,
            permission=self._client.config.member_permission,
        )

    def list_tables(
        self,
        app_token: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables",
            params=params,
        )
        return _unwrap_data(response)

    def iter_tables(self, app_token: str, *, page_size: int = 100) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_tables(app_token, page_size=page_size, page_token=page_token)
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_table(self, app_token: str, table: Mapping[str, object]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables",
            payload={"table": dict(table)},
        )
        return _unwrap_data(response)

    def batch_create_tables(self, app_token: str, tables: list[Mapping[str, object]]) -> Mapping[str, Any]:
        response = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/batch_create",
            payload={"tables": [dict(table) for table in tables]},
        )
        return _unwrap_data(response)

    def update_table(
        self,
        app_token: str,
        table_id: str,
        *,
        name: str,
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PATCH",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}",
            payload={"name": name},
        )
        return _unwrap_data(response)

    def delete_table(self, app_token: str, table_id: str) -> None:
        self._client.request_json("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}")

    def batch_delete_tables(self, app_token: str, table_ids: list[str]) -> None:
        self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/batch_delete",
            payload={"table_ids": list(table_ids)},
        )

    def list_fields(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "view_id": view_id,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            params=params,
        )
        return _unwrap_data(response)

    def iter_fields(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: Optional[str] = None,
        page_size: int = 100,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_fields(
                app_token,
                table_id,
                view_id=view_id,
                page_size=page_size,
                page_token=page_token,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def create_field(
        self,
        app_token: str,
        table_id: str,
        field: Mapping[str, object],
        *,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"client_token": client_token})
        response = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            params=params,
            payload=dict(field),
        )
        return _unwrap_data(response)

    def update_field(
        self,
        app_token: str,
        table_id: str,
        field_id: str,
        field: Mapping[str, object],
        *,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"client_token": client_token})
        response = self._client.request_json(
            "PUT",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
            params=params,
            payload=dict(field),
        )
        return _unwrap_data(response)

    def delete_field(
        self,
        app_token: str,
        table_id: str,
        field_id: str,
    ) -> None:
        self._client.request_json(
            "DELETE",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
        )

    def list_records(
        self,
        app_token: str,
        table_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        view_id: Optional[str] = None,
        user_id_type: Optional[str] = None,
        filter: Optional[str] = None,
        sort: Optional[str] = None,
        field_names: Optional[str] = None,
        text_field_as_array: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "view_id": view_id,
                "user_id_type": user_id_type,
                "filter": filter,
                "sort": sort,
                "field_names": field_names,
                "text_field_as_array": text_field_as_array,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params=params,
        )
        return _unwrap_data(response)

    def iter_records(
        self,
        app_token: str,
        table_id: str,
        *,
        page_size: int = 500,
        view_id: Optional[str] = None,
        user_id_type: Optional[str] = None,
        filter: Optional[str] = None,
        sort: Optional[str] = None,
        field_names: Optional[str] = None,
        text_field_as_array: Optional[bool] = None,
    ) -> Iterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = self.list_records(
                app_token,
                table_id,
                page_size=page_size,
                page_token=page_token,
                view_id=view_id,
                user_id_type=user_id_type,
                filter=filter,
                sort=sort,
                field_names=field_names,
                text_field_as_array=text_field_as_array,
            )
            yield from _iter_page_items(data)
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    def get_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        *,
        user_id_type: Optional[str] = None,
        text_field_as_array: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "text_field_as_array": text_field_as_array,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            params=params,
        )
        return _unwrap_data(response)

    def create_record(
        self,
        app_token: str,
        table_id: str,
        fields: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params=params,
            payload={"fields": dict(fields)},
        )
        return _unwrap_data(response)

    def batch_create_records(
        self,
        app_token: str,
        table_id: str,
        records: list[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        payload_records = [dict(record) for record in records]
        response = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            params=params,
            payload={"records": payload_records},
        )
        return _unwrap_data(response)

    def update_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        response = self._client.request_json(
            "PUT",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            params=params,
            payload={"fields": dict(fields)},
        )
        return _unwrap_data(response)

    def batch_update_records(
        self,
        app_token: str,
        table_id: str,
        records: list[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        payload_records = [dict(record) for record in records]
        response = self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
            params=params,
            payload={"records": payload_records},
        )
        return _unwrap_data(response)

    def delete_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
    ) -> None:
        self._client.request_json(
            "DELETE",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
        )

    def batch_delete_records(
        self,
        app_token: str,
        table_id: str,
        record_ids: list[str],
    ) -> None:
        self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete",
            payload={"records": list(record_ids)},
        )

    def _cleanup_default_tables(self, app_token: str, keep_table_id: str) -> None:
        try:
            tables_resp = self._client.request_json(
                "GET",
                f"/bitable/v1/apps/{app_token}/tables",
                params={"page_size": 100},
            )
        except Exception:
            return

        items = (tables_resp.get("data") or {}).get("items") or []
        for item in items:
            table_id = item.get("table_id")
            if not table_id or table_id == keep_table_id:
                continue
            try:
                self._client.request_json("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}")
            except Exception:
                continue


class AsyncBitableService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client
        self._drive_permissions = AsyncDrivePermissionService(feishu_client)

    async def create_from_csv(self, csv_path: str, app_name: str, table_name: str) -> tuple[str, str]:
        if not os.path.exists(csv_path):
            raise FileNotFoundError(csv_path)

        with open(csv_path, newline="", encoding="utf-8-sig") as file:
            reader = csv.reader(file)
            raw_headers = next(reader, [])

        headers = _prepare_headers(raw_headers)
        url_indices = _detect_url_indices(csv_path, len(headers))

        app_resp = await self._client.request_json(
            "POST",
            "/bitable/v1/apps",
            payload={"name": app_name},
        )
        app_token = app_resp["data"]["app"]["app_token"]
        app_url = app_resp["data"]["app"]["url"]

        fields = []
        for index, name in enumerate(headers):
            if index in url_indices:
                fields.append({"field_name": name, "type": 15, "ui_type": "Url"})
            else:
                fields.append({"field_name": name, "type": 1})
        table_payload: Dict[str, Dict[str, object]] = {"table": {"name": table_name}}
        if fields:
            table_payload["table"]["default_view_name"] = "Grid"
            table_payload["table"]["fields"] = fields
        table_resp = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables",
            payload=table_payload,
        )
        table_id = table_resp["data"]["table_id"]

        await self._cleanup_default_tables(app_token, table_id)

        rows = _iter_csv_rows(csv_path, headers, url_indices)
        for batch in _chunked(rows, 1000):
            await self._client.request_json(
                "POST",
                f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
                payload={"records": [{"fields": row} for row in batch]},
            )
        return app_token, app_url

    async def grant_edit_permission(
        self,
        app_token: str,
        member_id: str,
        member_id_type: str = MemberIdType.OPEN_ID.value,
    ) -> None:
        await self._drive_permissions.grant_edit_permission(
            app_token,
            member_id,
            member_id_type,
            resource_type=DriveResourceType.BITABLE,
            permission=self._client.config.member_permission,
        )

    async def list_tables(
        self,
        app_token: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"page_size": page_size, "page_token": page_token})
        response = await self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_tables(
        self,
        app_token: str,
        *,
        page_size: int = 100,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_tables(app_token, page_size=page_size, page_token=page_token)
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def create_table(self, app_token: str, table: Mapping[str, object]) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables",
            payload={"table": dict(table)},
        )
        return _unwrap_data(response)

    async def batch_create_tables(
        self,
        app_token: str,
        tables: list[Mapping[str, object]],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/batch_create",
            payload={"tables": [dict(table) for table in tables]},
        )
        return _unwrap_data(response)

    async def update_table(
        self,
        app_token: str,
        table_id: str,
        *,
        name: str,
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PATCH",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}",
            payload={"name": name},
        )
        return _unwrap_data(response)

    async def delete_table(self, app_token: str, table_id: str) -> None:
        await self._client.request_json("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}")

    async def batch_delete_tables(self, app_token: str, table_ids: list[str]) -> None:
        await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/batch_delete",
            payload={"table_ids": list(table_ids)},
        )

    async def list_fields(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: Optional[str] = None,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "view_id": view_id,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_fields(
        self,
        app_token: str,
        table_id: str,
        *,
        view_id: Optional[str] = None,
        page_size: int = 100,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_fields(
                app_token,
                table_id,
                view_id=view_id,
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

    async def create_field(
        self,
        app_token: str,
        table_id: str,
        field: Mapping[str, object],
        *,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"client_token": client_token})
        response = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            params=params,
            payload=dict(field),
        )
        return _unwrap_data(response)

    async def update_field(
        self,
        app_token: str,
        table_id: str,
        field_id: str,
        field: Mapping[str, object],
        *,
        client_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none({"client_token": client_token})
        response = await self._client.request_json(
            "PUT",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
            params=params,
            payload=dict(field),
        )
        return _unwrap_data(response)

    async def delete_field(
        self,
        app_token: str,
        table_id: str,
        field_id: str,
    ) -> None:
        await self._client.request_json(
            "DELETE",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{field_id}",
        )

    async def list_records(
        self,
        app_token: str,
        table_id: str,
        *,
        page_size: Optional[int] = None,
        page_token: Optional[str] = None,
        view_id: Optional[str] = None,
        user_id_type: Optional[str] = None,
        filter: Optional[str] = None,
        sort: Optional[str] = None,
        field_names: Optional[str] = None,
        text_field_as_array: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "page_size": page_size,
                "page_token": page_token,
                "view_id": view_id,
                "user_id_type": user_id_type,
                "filter": filter,
                "sort": sort,
                "field_names": field_names,
                "text_field_as_array": text_field_as_array,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params=params,
        )
        return _unwrap_data(response)

    async def iter_records(
        self,
        app_token: str,
        table_id: str,
        *,
        page_size: int = 500,
        view_id: Optional[str] = None,
        user_id_type: Optional[str] = None,
        filter: Optional[str] = None,
        sort: Optional[str] = None,
        field_names: Optional[str] = None,
        text_field_as_array: Optional[bool] = None,
    ) -> AsyncIterator[Mapping[str, Any]]:
        page_token: Optional[str] = None
        while True:
            data = await self.list_records(
                app_token,
                table_id,
                page_size=page_size,
                page_token=page_token,
                view_id=view_id,
                user_id_type=user_id_type,
                filter=filter,
                sort=sort,
                field_names=field_names,
                text_field_as_array=text_field_as_array,
            )
            for item in _iter_page_items(data):
                yield item
            if not _has_more(data):
                return
            page_token = _next_page_token(data)
            if not page_token:
                return

    async def get_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        *,
        user_id_type: Optional[str] = None,
        text_field_as_array: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "text_field_as_array": text_field_as_array,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            params=params,
        )
        return _unwrap_data(response)

    async def create_record(
        self,
        app_token: str,
        table_id: str,
        fields: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records",
            params=params,
            payload={"fields": dict(fields)},
        )
        return _unwrap_data(response)

    async def batch_create_records(
        self,
        app_token: str,
        table_id: str,
        records: list[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        payload_records = [dict(record) for record in records]
        response = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            params=params,
            payload={"records": payload_records},
        )
        return _unwrap_data(response)

    async def update_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
        fields: Mapping[str, object],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        response = await self._client.request_json(
            "PUT",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
            params=params,
            payload={"fields": dict(fields)},
        )
        return _unwrap_data(response)

    async def batch_update_records(
        self,
        app_token: str,
        table_id: str,
        records: list[Mapping[str, object]],
        *,
        user_id_type: Optional[str] = None,
        client_token: Optional[str] = None,
        ignore_consistency_check: Optional[bool] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "user_id_type": user_id_type,
                "client_token": client_token,
                "ignore_consistency_check": ignore_consistency_check,
            }
        )
        payload_records = [dict(record) for record in records]
        response = await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_update",
            params=params,
            payload={"records": payload_records},
        )
        return _unwrap_data(response)

    async def delete_record(
        self,
        app_token: str,
        table_id: str,
        record_id: str,
    ) -> None:
        await self._client.request_json(
            "DELETE",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
        )

    async def batch_delete_records(
        self,
        app_token: str,
        table_id: str,
        record_ids: list[str],
    ) -> None:
        await self._client.request_json(
            "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_delete",
            payload={"records": list(record_ids)},
        )

    async def _cleanup_default_tables(self, app_token: str, keep_table_id: str) -> None:
        try:
            tables_resp = await self._client.request_json(
                "GET",
                f"/bitable/v1/apps/{app_token}/tables",
                params={"page_size": 100},
            )
        except Exception:
            return

        items = (tables_resp.get("data") or {}).get("items") or []
        for item in items:
            table_id = item.get("table_id")
            if not table_id or table_id == keep_table_id:
                continue
            try:
                await self._client.request_json("DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}")
            except Exception:
                continue
