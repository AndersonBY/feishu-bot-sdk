from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, Optional


def _to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped)
        except ValueError:
            return default
    return default


def _to_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _wrap(value: Any) -> Any:
    if isinstance(value, Mapping):
        return Struct({str(k): v for k, v in value.items()})
    if isinstance(value, list):
        return [_wrap(item) for item in value]
    return value


class Struct(Mapping[str, Any]):
    def __init__(self, data: Mapping[str, Any] | None = None) -> None:
        self._data = {str(k): v for k, v in (data or {}).items()}

    def __getitem__(self, key: str) -> Any:
        return _wrap(self._data[key])

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return _wrap(self._data[name])
        raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

    def to_dict(self) -> dict[str, Any]:
        return {key: _to_jsonable(value) for key, value in self._data.items()}


class DataResponse(Mapping[str, Any]):
    def __init__(
        self,
        *,
        code: int,
        msg: Optional[str],
        data: Struct,
        raw: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.msg = msg
        self.data = data
        self.raw = {str(k): v for k, v in (raw or {}).items()}

    @property
    def ok(self) -> bool:
        return self.code == 0

    @classmethod
    def from_raw(cls, payload: Mapping[str, Any]) -> "DataResponse":
        data_raw = payload.get("data")
        data = Struct(data_raw if isinstance(data_raw, Mapping) else {})
        return cls(
            code=_to_int(payload.get("code"), default=0),
            msg=_to_str(payload.get("msg")),
            data=data,
            raw=payload,
        )

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)

    def __getattr__(self, name: str) -> Any:
        if name in self.raw and name not in {"code", "msg", "data", "raw"}:
            return _wrap(self.raw[name])
        return getattr(self.data, name)

    def to_dict(self, *, include_meta: bool = True, include_raw: bool = False) -> dict[str, Any]:
        payload = self.data.to_dict()
        if include_meta:
            payload = {
                "code": self.code,
                "msg": self.msg,
                "data": payload,
            }
        if include_raw:
            payload["raw"] = _to_jsonable(self.raw)
        return payload


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, DataResponse):
        return value.to_dict(include_meta=True, include_raw=False)
    if isinstance(value, Struct):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value
