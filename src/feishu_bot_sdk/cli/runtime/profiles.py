from __future__ import annotations

from .config_store import CLIConfig, CLIProfile, load_cli_config, resolve_cli_profile_name


def resolve_cli_profile(
    profile: str | None = None,
    *,
    config: CLIConfig | None = None,
) -> tuple[str, CLIProfile | None, CLIConfig]:
    active_config = config or load_cli_config()
    profile_name = resolve_cli_profile_name(profile, config=active_config)
    return profile_name, active_config.profile(profile_name), active_config


def list_cli_profiles(*, config: CLIConfig | None = None) -> list[CLIProfile]:
    active_config = config or load_cli_config()
    return [active_config.profiles[name] for name in sorted(active_config.profiles)]


__all__ = ["list_cli_profiles", "resolve_cli_profile"]
