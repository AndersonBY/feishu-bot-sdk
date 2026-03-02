from dataclasses import dataclass
from typing import Optional


_DEFAULT_FEISHU_BASE_URL = "https://open.feishu.cn/open-apis"


@dataclass(frozen=True)
class FeishuConfig:
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    base_url: str = _DEFAULT_FEISHU_BASE_URL
    auth_mode: str = "tenant"
    access_token: Optional[str] = None
    app_access_token: Optional[str] = None
    user_access_token: Optional[str] = None
    user_refresh_token: Optional[str] = None
    doc_url_prefix: Optional[str] = None
    doc_folder_token: Optional[str] = None
    member_permission: str = "edit"
    timeout_seconds: float = 30.0
    rate_limit_enabled: bool = True
    rate_limit_base_qps: float = 5.0
    rate_limit_min_qps: float = 1.0
    rate_limit_max_qps: float = 50.0
    rate_limit_increase_factor: float = 1.05
    rate_limit_decrease_factor: float = 0.5
    rate_limit_cooldown_seconds: float = 1.0
    rate_limit_max_wait_seconds: float = 30.0

    def __post_init__(self) -> None:
        normalized_mode = str(self.auth_mode or "").strip().lower()
        if normalized_mode not in {"tenant", "user"}:
            raise ValueError("auth_mode must be either 'tenant' or 'user'")
        object.__setattr__(self, "auth_mode", normalized_mode)
