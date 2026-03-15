from typing import Any, Iterator, Mapping, Optional

from ..response import DataResponse


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


def _next_page_token(data: Mapping[str, Any]) -> Optional[str]:
    token = data.get("page_token")
    if isinstance(token, str) and token:
        return token
    return None


def _has_more(data: Mapping[str, Any]) -> bool:
    return bool(data.get("has_more"))


def _iter_page_files(data: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    files = data.get("files")
    if not isinstance(files, list):
        return
    for item in files:
        if isinstance(item, Mapping):
            yield item
