from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class EventEnvelope:
    schema: str
    event_type: str
    event_id: Optional[str] = None
    token: Optional[str] = None
    tenant_key: Optional[str] = None
    app_id: Optional[str] = None
    create_time: Optional[str] = None
    challenge: Optional[str] = None
    is_callback: bool = False
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_url_verification(self) -> bool:
        return self.event_type == "url_verification"


@dataclass(frozen=True)
class EventContext:
    envelope: EventEnvelope
    payload: Mapping[str, Any] = field(default_factory=dict)
    event: Any = None
