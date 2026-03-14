from __future__ import annotations

from typing import Any, Mapping, Optional


class CardCallbackResponse:
    """Helpers for building card.action.trigger callback responses.

    Usage::

        # Immediate toast
        return CardCallbackResponse.toast("Done!")

        # Return an updated card inline
        return CardCallbackResponse.card({"elements": [...]})

        # Return arbitrary inline payload
        return CardCallbackResponse.inline(toast={...}, card={...})
    """

    @staticmethod
    def toast(
        content: str,
        *,
        type: str = "info",
        i18n: Optional[Mapping[str, str]] = None,
    ) -> dict[str, Any]:
        toast_payload: dict[str, Any] = {"type": type, "content": content}
        if i18n:
            toast_payload["i18n"] = {str(k): str(v) for k, v in i18n.items()}
        return {"toast": toast_payload}

    @staticmethod
    def card(
        card: Mapping[str, Any],
        *,
        card_type: str = "raw",
    ) -> dict[str, Any]:
        if card_type == "raw":
            return {"card": dict(card)}
        return {"card": {"type": card_type, "data": dict(card)}}

    @staticmethod
    def inline(**payload: Any) -> dict[str, Any]:
        return dict(payload)
