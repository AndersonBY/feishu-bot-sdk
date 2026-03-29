from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...token_store import StoredUserToken, TokenStore, default_token_store_path
from .config_store import CLIConfig, SecretReference, make_profile, save_cli_config


@dataclass(frozen=True)
class TokenStoreMigrationResult:
    source_path: Path
    token_store_path: Path
    config_path: Path
    imported_profiles: tuple[str, ...]
    default_profile: str


def load_token_store_profiles(path: Path | None = None) -> dict[str, StoredUserToken]:
    target = path or default_token_store_path()
    return TokenStore(target).list_profiles()


def migrate_token_store_to_cli_config(
    config: CLIConfig,
    *,
    source_path: Path | None = None,
    token_store_path: Path | None = None,
    config_path: Path | None = None,
    default_profile: str | None = None,
    only_profiles: list[str] | tuple[str, ...] | None = None,
    app_id: str | None = None,
    app_secret_refs: dict[str, SecretReference] | None = None,
    auth_mode: str | None = None,
    base_url: str | None = None,
    timeout_seconds: float | None = None,
) -> tuple[CLIConfig, TokenStoreMigrationResult]:
    resolved_source_path = source_path or default_token_store_path()
    resolved_token_store_path = token_store_path or resolved_source_path
    available_profiles = load_token_store_profiles(resolved_source_path)

    requested_profiles = _normalize_profile_names(only_profiles)
    selected_names = (
        [name for name in requested_profiles if name in available_profiles]
        if requested_profiles
        else sorted(available_profiles)
    )
    if not selected_names:
        raise ValueError(f"token store {resolved_source_path} does not contain any importable profiles")

    missing_requested = [name for name in requested_profiles if name not in available_profiles]
    if missing_requested:
        missing_text = ", ".join(sorted(missing_requested))
        raise ValueError(f"requested token store profiles do not exist: {missing_text}")

    updated = config
    secret_refs = app_secret_refs or {}
    normalized_app_id = _optional_text(app_id)
    normalized_auth_mode = _optional_text(auth_mode)
    normalized_base_url = _optional_text(base_url)
    normalized_token_store_path = str(resolved_token_store_path)

    for name in selected_names:
        existing = updated.profile(name)
        profile = make_profile(
            name,
            app_id=normalized_app_id or (existing.app_id if existing else None),
            app_secret_ref=secret_refs.get(name) or (existing.app_secret_ref if existing else None),
            auth_mode=normalized_auth_mode or (existing.auth_mode if existing else None),
            base_url=normalized_base_url or (existing.base_url if existing else None),
            timeout_seconds=timeout_seconds if timeout_seconds is not None else (existing.timeout_seconds if existing else None),
            default_identity=existing.default_identity if existing else None,
            token_store_path=normalized_token_store_path,
        )
        updated = updated.with_profile(profile, set_default=False)

    resolved_default_profile = _resolve_default_profile(
        default_profile=default_profile,
        current_config=updated,
        imported_profiles=selected_names,
    )
    updated = updated.with_default_profile(resolved_default_profile)
    saved_path = save_cli_config(updated, path=config_path)
    return updated, TokenStoreMigrationResult(
        source_path=resolved_source_path,
        token_store_path=resolved_token_store_path,
        config_path=saved_path,
        imported_profiles=tuple(selected_names),
        default_profile=resolved_default_profile,
    )


def _resolve_default_profile(
    *,
    default_profile: str | None,
    current_config: CLIConfig,
    imported_profiles: list[str],
) -> str:
    requested = _optional_text(default_profile)
    if requested:
        if requested not in current_config.profiles:
            raise ValueError(f"default profile {requested!r} is not available after migration")
        return requested
    current_default = _optional_text(current_config.default_profile)
    if current_default and current_default in current_config.profiles:
        return current_default
    if "default" in imported_profiles:
        return "default"
    return imported_profiles[0]


def _normalize_profile_names(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    normalized: list[str] = []
    for raw in values:
        value = _optional_text(raw)
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


__all__ = [
    "TokenStoreMigrationResult",
    "load_token_store_profiles",
    "migrate_token_store_to_cli_config",
]
