from __future__ import annotations

import json
from typing import Any, Mapping

from ...response import DataResponse


def _serialize_content(content: Mapping[str, Any]) -> str:
    return json.dumps(dict(content), ensure_ascii=False)


def _drop_none(params: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in params.items() if value is not None}


def _unwrap_data(response: Mapping[str, Any]) -> DataResponse:
    return DataResponse.from_raw(response)


__all__ = ["_serialize_content", "_drop_none", "_unwrap_data"]
