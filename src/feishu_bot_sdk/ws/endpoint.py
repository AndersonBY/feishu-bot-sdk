from dataclasses import dataclass
from typing import Any, Mapping, Optional
from urllib.parse import parse_qs, urlparse

from ..http_client import AsyncJsonHttpClient, JsonHttpClient
from .constants import WS_DEFAULT_DOMAIN, WS_ENDPOINT_URI
from .errors import WSEndpointError


@dataclass
class WSRemoteConfig:
    reconnect_count: int = -1
    reconnect_interval_seconds: float = 120.0
    reconnect_nonce_seconds: float = 30.0
    ping_interval_seconds: float = 120.0


@dataclass
class WSEndpoint:
    url: str
    device_id: Optional[str]
    service_id: Optional[str]
    remote_config: WSRemoteConfig


def fetch_ws_endpoint(
    *,
    app_id: str,
    app_secret: str,
    domain: str = WS_DEFAULT_DOMAIN,
    timeout_seconds: float = 30.0,
    http_client: Optional[JsonHttpClient] = None,
) -> WSEndpoint:
    client = http_client or JsonHttpClient(timeout_seconds=timeout_seconds)
    data = client.request_json(
        "POST",
        f"{domain}{WS_ENDPOINT_URI}",
        headers={"locale": "zh"},
        payload={"AppID": app_id, "AppSecret": app_secret},
        timeout_seconds=timeout_seconds,
    )
    return _parse_endpoint_response(data)


async def fetch_ws_endpoint_async(
    *,
    app_id: str,
    app_secret: str,
    domain: str = WS_DEFAULT_DOMAIN,
    timeout_seconds: float = 30.0,
    http_client: Optional[AsyncJsonHttpClient] = None,
) -> WSEndpoint:
    client = http_client or AsyncJsonHttpClient(timeout_seconds=timeout_seconds)
    data = await client.request_json(
        "POST",
        f"{domain}{WS_ENDPOINT_URI}",
        headers={"locale": "zh"},
        payload={"AppID": app_id, "AppSecret": app_secret},
        timeout_seconds=timeout_seconds,
    )
    return _parse_endpoint_response(data)


def _parse_endpoint_response(data: dict) -> WSEndpoint:
    code = data.get("code")
    if code != 0:
        raise WSEndpointError(f"fetch ws endpoint failed: {data}")
    payload = data.get("data")
    if not isinstance(payload, dict):
        raise WSEndpointError("fetch ws endpoint failed: missing data")
    url = payload.get("URL")
    if not isinstance(url, str) or not url:
        raise WSEndpointError("fetch ws endpoint failed: missing URL")
    remote_config = _parse_remote_config(payload.get("ClientConfig"))
    query = parse_qs(urlparse(url).query)
    device_id = _first(query.get("device_id"))
    service_id = _first(query.get("service_id"))
    return WSEndpoint(
        url=url,
        device_id=device_id,
        service_id=service_id,
        remote_config=remote_config,
    )


def _parse_remote_config(payload: object) -> WSRemoteConfig:
    if not isinstance(payload, Mapping):
        return WSRemoteConfig()
    values = {str(key): value for key, value in payload.items()}
    return WSRemoteConfig(
        reconnect_count=_as_int(values.get("ReconnectCount"), default=-1),
        reconnect_interval_seconds=_as_float(values.get("ReconnectInterval"), default=120.0),
        reconnect_nonce_seconds=_as_float(values.get("ReconnectNonce"), default=30.0),
        ping_interval_seconds=_as_float(values.get("PingInterval"), default=120.0),
    )


def _first(items: Optional[list]) -> Optional[str]:
    if not items:
        return None
    first = items[0]
    if isinstance(first, str):
        return first
    return str(first)


def _as_int(value: Any, *, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, *, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
