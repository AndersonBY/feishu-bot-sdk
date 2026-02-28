from typing import Any, Dict, Mapping, Optional

from ..events import EventContext, EventHandlerRegistry, build_event_context
from .challenge import build_challenge_response, extract_challenge
from .crypto import decode_webhook_body
from .errors import WebhookHandlerError, WebhookTokenError
from .security import verify_signature


class WebhookReceiver:
    def __init__(
        self,
        handler_registry: EventHandlerRegistry,
        *,
        encrypt_key: Optional[str] = None,
        verification_token: Optional[str] = None,
        is_callback: bool = False,
        verify_signatures: bool = True,
        timestamp_tolerance_seconds: float = 300.0,
    ) -> None:
        self._handlers = handler_registry
        self._encrypt_key = encrypt_key
        self._verification_token = verification_token
        self._is_callback = is_callback
        self._verify_signatures = verify_signatures
        self._timestamp_tolerance_seconds = timestamp_tolerance_seconds

    def handle(self, headers: Mapping[str, str], raw_body: bytes) -> Dict[str, Any]:
        context = self._build_context(raw_body)
        if context.envelope.is_url_verification:
            challenge = extract_challenge(context.payload)
            return build_challenge_response(challenge or "")
        self._validate_token(context)
        self._validate_signature(headers, raw_body)
        return _normalize_handler_result(self._handlers.dispatch(context), is_callback=self._is_callback)

    async def ahandle(self, headers: Mapping[str, str], raw_body: bytes) -> Dict[str, Any]:
        context = self._build_context(raw_body)
        if context.envelope.is_url_verification:
            challenge = extract_challenge(context.payload)
            return build_challenge_response(challenge or "")
        self._validate_token(context)
        self._validate_signature(headers, raw_body)
        return _normalize_handler_result(
            await self._handlers.adispatch(context),
            is_callback=self._is_callback,
        )

    def _build_context(self, raw_body: bytes) -> EventContext:
        payload = decode_webhook_body(raw_body, encrypt_key=self._encrypt_key)
        return build_event_context(payload, is_callback=self._is_callback)

    def _validate_token(self, context: EventContext) -> None:
        if not self._verification_token:
            return
        incoming_token = context.envelope.token
        if incoming_token and incoming_token != self._verification_token:
            raise WebhookTokenError("verification token mismatch")

    def _validate_signature(self, headers: Mapping[str, str], raw_body: bytes) -> None:
        if not self._verify_signatures:
            return
        if not self._encrypt_key:
            return
        verify_signature(
            headers,
            raw_body,
            encrypt_key=self._encrypt_key,
            tolerance_seconds=self._timestamp_tolerance_seconds,
        )


def _normalize_handler_result(result: Any, *, is_callback: bool) -> Dict[str, Any]:
    if result is None:
        return {"msg": "success"}
    if isinstance(result, Mapping):
        return {str(k): v for k, v in result.items()}
    if is_callback:
        raise WebhookHandlerError("callback handler result must be a mapping or None")
    return {"msg": "success"}
