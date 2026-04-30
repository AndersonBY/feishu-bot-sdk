from __future__ import annotations

from typing import Any, Mapping, Sequence


def apply_jq_filter(payload: Any, expression: str | None) -> Any:
    expr = str(expression or "").strip()
    if not expr or expr == ".":
        return payload
    if not expr.startswith(".") or any(token in expr for token in ("|", "[]", "(", ")")):
        raise ValueError(f"unsupported jq expression: {expression}")
    current = payload
    for part in [item for item in expr[1:].split(".") if item]:
        current = _select_part(current, part, expression=expression)
    return current


def _select_part(current: Any, part: str, *, expression: str | None) -> Any:
    if isinstance(current, Mapping):
        return current.get(part)
    if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
        try:
            index = int(part)
        except ValueError as exc:
            raise ValueError(f"unsupported jq expression: {expression}") from exc
        try:
            return current[index]
        except IndexError:
            return None
    return None


__all__ = [name for name in globals() if not name.startswith("__")]

