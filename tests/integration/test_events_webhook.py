import base64
import hashlib
import json
import os
import time

from Crypto.Cipher import AES

from feishu_bot_sdk import (
    FeishuEventRegistry,
    MemoryIdempotencyStore,
    WebhookReceiver,
    build_idempotency_key,
    parse_event_envelope,
)
from feishu_bot_sdk.webhook.security import compute_signature


def test_webhook_url_verification_returns_challenge():
    registry = FeishuEventRegistry()
    receiver = WebhookReceiver(registry)
    raw_body = json.dumps(
        {
            "challenge": "abc123",
            "type": "url_verification",
            "token": "test-token",
        }
    ).encode("utf-8")

    response = receiver.handle({}, raw_body)
    assert response == {"challenge": "abc123"}


def test_webhook_encrypted_payload_signature_and_dispatch():
    received: list[str] = []
    registry = FeishuEventRegistry()
    registry.on_im_message_receive(lambda event: received.append(event.message_id or ""))

    encrypt_key = "test-encrypt-key"
    receiver = WebhookReceiver(registry, encrypt_key=encrypt_key)

    plaintext_payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_123",
            "event_type": "im.message.receive_v1",
        },
        "event": {
            "message": {
                "message_id": "om_123",
                "message_type": "text",
                "content": "{\"text\":\"hi\"}",
            }
        },
    }
    encrypted_body = json.dumps(
        {
            "encrypt": _encrypt_payload(plaintext_payload, encrypt_key),
        }
    ).encode("utf-8")
    timestamp = str(int(time.time()))
    nonce = "nonce-1"
    signature = compute_signature(timestamp, nonce, encrypt_key, encrypted_body)

    response = receiver.handle(
        {
            "X-Lark-Request-Timestamp": timestamp,
            "X-Lark-Request-Nonce": nonce,
            "X-Lark-Signature": signature,
        },
        encrypted_body,
    )

    assert response == {"msg": "success"}
    assert received == ["om_123"]


def test_idempotency_store_with_event_id():
    payload = {
        "schema": "2.0",
        "header": {
            "event_id": "evt_1",
            "event_type": "im.message.receive_v1",
        },
        "event": {},
    }
    envelope = parse_event_envelope(payload)
    key = build_idempotency_key(envelope)
    assert key == "evt_1"

    store = MemoryIdempotencyStore()
    assert store.mark_once(key) is True
    assert store.mark_once(key) is False
    assert store.seen(key) is True


def _encrypt_payload(payload: dict, encrypt_key: str) -> str:
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    padded = _pkcs7_pad(plaintext)
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(iv + encrypted).decode("utf-8")


def _pkcs7_pad(data: bytes) -> bytes:
    pad_size = AES.block_size - (len(data) % AES.block_size)
    return data + bytes([pad_size]) * pad_size
