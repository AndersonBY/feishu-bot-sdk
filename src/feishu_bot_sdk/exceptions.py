from typing import Mapping, Optional


class SDKError(RuntimeError):
    pass


class ConfigurationError(SDKError):
    pass


class HTTPRequestError(SDKError):
    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        response_headers: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text
        self.response_headers = dict(response_headers or {})


class FeishuError(SDKError):
    pass
