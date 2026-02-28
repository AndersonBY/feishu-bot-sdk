import random
from dataclasses import dataclass


@dataclass
class ReconnectPolicy:
    retry_count: int = -1
    interval_seconds: float = 120.0
    initial_jitter_seconds: float = 30.0

    def should_retry(self, attempt: int) -> bool:
        if self.retry_count < 0:
            return True
        return attempt < self.retry_count

    def get_delay_seconds(self, attempt: int) -> float:
        if attempt == 0 and self.initial_jitter_seconds > 0:
            return random.random() * self.initial_jitter_seconds
        return max(self.interval_seconds, 0.0)
