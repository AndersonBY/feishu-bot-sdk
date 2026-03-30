from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


def metadata_root() -> Path:
    return Path(__file__).resolve().parents[1] / "metadata"


def services_root() -> Path:
    return metadata_root() / "services"


@dataclass(frozen=True)
class MethodSpec:
    service: str
    service_path: str
    resource: str
    name: str
    raw: dict[str, Any]

    @property
    def cli_path(self) -> str:
        return f"{self.service}.{self.resource}.{self.name}"

    @property
    def id(self) -> str:
        return str(self.raw.get("id") or self.cli_path)

    @property
    def description(self) -> str:
        return str(self.raw.get("description") or "")

    @property
    def http_method(self) -> str:
        return str(self.raw.get("httpMethod") or "GET").upper()

    @property
    def relative_path(self) -> str:
        return str(self.raw.get("path") or "")

    @property
    def full_path(self) -> str:
        base = self.service_path.strip("/")
        path = self.relative_path.strip("/")
        if not base:
            return f"/{path}"
        if not path:
            return f"/{base}"
        return f"/{base}/{path}"

    @property
    def access_tokens(self) -> tuple[str, ...]:
        values = self.raw.get("accessTokens")
        if not isinstance(values, list):
            return ()
        return tuple(str(item) for item in values if str(item))

    @property
    def supported_identities(self) -> tuple[str, ...]:
        identities: list[str] = []
        for token in self.access_tokens:
            if token == "tenant":
                identities.append("bot")
            elif token in {"user", "bot"}:
                identities.append(token)
        deduped: list[str] = []
        for item in identities:
            if item not in deduped:
                deduped.append(item)
        return tuple(deduped)

    @property
    def scopes(self) -> tuple[str, ...]:
        values = self.raw.get("scopes")
        if not isinstance(values, list):
            return ()
        return tuple(str(item) for item in values if str(item))

    @property
    def required_scopes(self) -> tuple[str, ...]:
        values = self.raw.get("requiredScopes")
        if not isinstance(values, list):
            return ()
        return tuple(str(item) for item in values if str(item))

    @property
    def parameters(self) -> dict[str, Any]:
        data = self.raw.get("parameters")
        if isinstance(data, dict):
            return data
        return {}

    @property
    def request_body(self) -> dict[str, Any]:
        data = self.raw.get("requestBody")
        if isinstance(data, dict):
            return data
        return {}

    @property
    def response_body(self) -> dict[str, Any]:
        data = self.raw.get("responseBody")
        if isinstance(data, dict):
            return data
        return {}

    @property
    def doc_url(self) -> str:
        return str(self.raw.get("docUrl") or "")

    @property
    def danger(self) -> bool:
        return bool(self.raw.get("danger"))


@dataclass(frozen=True)
class ResourceSpec:
    service: str
    service_path: str
    name: str
    raw: dict[str, Any]

    @property
    def methods(self) -> tuple[MethodSpec, ...]:
        items = self.raw.get("methods")
        if not isinstance(items, dict):
            return ()
        return tuple(
            MethodSpec(
                service=self.service,
                service_path=self.service_path,
                resource=self.name,
                name=method_name,
                raw=method_raw if isinstance(method_raw, dict) else {},
            )
            for method_name, method_raw in sorted(items.items())
        )


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    service_path: str
    title: str
    description: str
    version: str
    raw: dict[str, Any]

    @property
    def resources(self) -> tuple[ResourceSpec, ...]:
        items = self.raw.get("resources")
        if not isinstance(items, dict):
            return ()
        return tuple(
            ResourceSpec(
                service=self.name,
                service_path=self.service_path,
                name=resource_name,
                raw=resource_raw if isinstance(resource_raw, dict) else {},
            )
            for resource_name, resource_raw in sorted(items.items())
        )

    @property
    def methods(self) -> tuple[MethodSpec, ...]:
        result: list[MethodSpec] = []
        for resource in self.resources:
            result.extend(resource.methods)
        return tuple(result)


@dataclass(frozen=True)
class MetadataSnapshot:
    version: str
    services: tuple[ServiceSpec, ...]


def metadata_available() -> bool:
    root = services_root()
    return root.exists() and any(path.is_file() for path in root.glob("*.json"))


@lru_cache(maxsize=1)
def load_metadata_snapshot() -> MetadataSnapshot:
    root = services_root()
    services: list[ServiceSpec] = []
    if root.exists():
        for path in sorted(root.glob("*.json")):
            raw = _load_json(path)
            services.append(
                ServiceSpec(
                    name=str(raw.get("name") or path.stem),
                    service_path=str(raw.get("servicePath") or ""),
                    title=str(raw.get("title") or raw.get("name") or path.stem),
                    description=str(raw.get("description") or ""),
                    version=str(raw.get("version") or ""),
                    raw=raw,
                )
            )
    meta_version = _load_json(metadata_root() / "meta_version.json")
    return MetadataSnapshot(version=str(meta_version.get("version") or ""), services=tuple(services))


def list_services() -> tuple[ServiceSpec, ...]:
    return load_metadata_snapshot().services


def get_service(name: str) -> ServiceSpec | None:
    normalized = str(name).strip()
    for service in list_services():
        if service.name == normalized:
            return service
    return None


def iter_methods(service_names: Iterable[str] | None = None) -> Iterable[MethodSpec]:
    allowed = {str(name).strip() for name in service_names or [] if str(name).strip()}
    for service in list_services():
        if allowed and service.name not in allowed:
            continue
        yield from service.methods


def find_method(schema_path: str) -> MethodSpec | None:
    parts = [item.strip() for item in str(schema_path or "").split(".") if item.strip()]
    if len(parts) != 3:
        return None
    service = get_service(parts[0])
    if service is None:
        return None
    for method in service.methods:
        if method.resource == parts[1] and method.name == parts[2]:
            return method
    return None


def list_schema_paths() -> list[str]:
    return sorted(method.cli_path for method in iter_methods())


def summarize_shape(value: Any, *, depth: int = 0) -> Any:
    if depth >= 3:
        if isinstance(value, dict):
            return "{...}"
        if isinstance(value, list):
            return "[...]"
        return value
    if isinstance(value, dict):
        return {str(key): summarize_shape(item, depth=depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        return [summarize_shape(value[0], depth=depth + 1)] if value else []
    return value


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


__all__ = [
    "MetadataSnapshot",
    "MethodSpec",
    "ResourceSpec",
    "ServiceSpec",
    "find_method",
    "get_service",
    "iter_methods",
    "list_schema_paths",
    "list_services",
    "load_metadata_snapshot",
    "metadata_available",
    "metadata_root",
    "summarize_shape",
]
