from dataclasses import dataclass
from typing import Optional


@dataclass
class HeartbeatConfig:
    interval_seconds: float = 120.0
    last_pong_at: Optional[float] = None

    def update_interval(self, interval_seconds: Optional[float]) -> None:
        if interval_seconds is None:
            return
        if interval_seconds <= 0:
            return
        self.interval_seconds = interval_seconds
