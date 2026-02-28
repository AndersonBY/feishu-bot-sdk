from typing import Any, Dict, Mapping, Optional

from .errors import WebhookChallengeError


def extract_challenge(payload: Mapping[str, Any]) -> Optional[str]:
    value = payload.get("challenge")
    if isinstance(value, str) and value:
        return value
    return None


def build_challenge_response(challenge: str) -> Dict[str, str]:
    if not challenge:
        raise WebhookChallengeError("challenge is required")
    return {"challenge": challenge}
