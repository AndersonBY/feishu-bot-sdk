from typing import Any, Mapping, Optional

from .feishu import AsyncFeishuClient, FeishuClient
from .response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


class SheetsService:
    def __init__(self, feishu_client: FeishuClient) -> None:
        self._client = feishu_client

    def create_spreadsheet(
        self,
        *,
        title: Optional[str] = None,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none({"title": title, "folder_token": folder_token})
        response = self._client.request_json(
            "POST",
            "/sheets/v3/spreadsheets",
            payload=payload,
        )
        return _unwrap_data(response)

    def get_spreadsheet_info(self, token: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/sheets/v3/spreadsheets/{token}",
        )
        return _unwrap_data(response)

    def list_sheets(self, token: str) -> Mapping[str, Any]:
        response = self._client.request_json(
            "GET",
            f"/sheets/v3/spreadsheets/{token}/sheets/query",
        )
        return _unwrap_data(response)

    def read_values(
        self,
        token: str,
        range: str,
        *,
        value_render_option: Optional[str] = None,
        date_time_render_option: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "value_render_option": value_render_option,
                "date_time_render_option": date_time_render_option,
            }
        )
        response = self._client.request_json(
            "GET",
            f"/sheets/v2/spreadsheets/{token}/values/{range}",
            params=params,
        )
        return _unwrap_data(response)

    def write_values(
        self,
        token: str,
        *,
        value_range: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = self._client.request_json(
            "PUT",
            f"/sheets/v2/spreadsheets/{token}/values",
            payload={"valueRange": dict(value_range)},
        )
        return _unwrap_data(response)

    def append_values(
        self,
        token: str,
        *,
        value_range: Mapping[str, object],
        insert_data_option: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "valueRange": dict(value_range),
                "insertDataOption": insert_data_option,
            }
        )
        response = self._client.request_json(
            "POST",
            f"/sheets/v2/spreadsheets/{token}/values_append",
            payload=payload,
        )
        return _unwrap_data(response)

    def find_cells(
        self,
        token: str,
        sheet_id: str,
        *,
        find: str,
        find_condition: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {"find": find}
        if find_condition is not None:
            payload["find_condition"] = dict(find_condition)
        response = self._client.request_json(
            "POST",
            f"/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/find",
            payload=payload,
        )
        return _unwrap_data(response)


class AsyncSheetsService:
    def __init__(self, feishu_client: AsyncFeishuClient) -> None:
        self._client = feishu_client

    async def create_spreadsheet(
        self,
        *,
        title: Optional[str] = None,
        folder_token: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none({"title": title, "folder_token": folder_token})
        response = await self._client.request_json(
            "POST",
            "/sheets/v3/spreadsheets",
            payload=payload,
        )
        return _unwrap_data(response)

    async def get_spreadsheet_info(self, token: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/sheets/v3/spreadsheets/{token}",
        )
        return _unwrap_data(response)

    async def list_sheets(self, token: str) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "GET",
            f"/sheets/v3/spreadsheets/{token}/sheets/query",
        )
        return _unwrap_data(response)

    async def read_values(
        self,
        token: str,
        range: str,
        *,
        value_render_option: Optional[str] = None,
        date_time_render_option: Optional[str] = None,
    ) -> Mapping[str, Any]:
        params = _drop_none(
            {
                "value_render_option": value_render_option,
                "date_time_render_option": date_time_render_option,
            }
        )
        response = await self._client.request_json(
            "GET",
            f"/sheets/v2/spreadsheets/{token}/values/{range}",
            params=params,
        )
        return _unwrap_data(response)

    async def write_values(
        self,
        token: str,
        *,
        value_range: Mapping[str, object],
    ) -> Mapping[str, Any]:
        response = await self._client.request_json(
            "PUT",
            f"/sheets/v2/spreadsheets/{token}/values",
            payload={"valueRange": dict(value_range)},
        )
        return _unwrap_data(response)

    async def append_values(
        self,
        token: str,
        *,
        value_range: Mapping[str, object],
        insert_data_option: Optional[str] = None,
    ) -> Mapping[str, Any]:
        payload = _drop_none(
            {
                "valueRange": dict(value_range),
                "insertDataOption": insert_data_option,
            }
        )
        response = await self._client.request_json(
            "POST",
            f"/sheets/v2/spreadsheets/{token}/values_append",
            payload=payload,
        )
        return _unwrap_data(response)

    async def find_cells(
        self,
        token: str,
        sheet_id: str,
        *,
        find: str,
        find_condition: Optional[Mapping[str, object]] = None,
    ) -> Mapping[str, Any]:
        payload: dict[str, object] = {"find": find}
        if find_condition is not None:
            payload["find_condition"] = dict(find_condition)
        response = await self._client.request_json(
            "POST",
            f"/sheets/v3/spreadsheets/{token}/sheets/{sheet_id}/find",
            payload=payload,
        )
        return _unwrap_data(response)
