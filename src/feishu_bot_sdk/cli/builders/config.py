from __future__ import annotations

import argparse

from ..commands import (
    _cmd_config_init,
    _cmd_config_list_profiles,
    _cmd_config_migrate_token_store,
    _cmd_config_remove_profile,
    _cmd_config_set_default_profile,
    _cmd_config_show,
)
from ..settings import HELP_FORMATTER as _HELP_FORMATTER


def _build_config_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    shared: argparse.ArgumentParser,
) -> None:
    config_parser = subparsers.add_parser(
        "config",
        help="Manage CLI profiles and stored app credentials",
        description=(
            "Manage CLI profiles, app credentials, and default profile selection.\n"
            "Prefer `config init --app-secret-stdin` over passing app secrets on the command line."
        ),
        formatter_class=_HELP_FORMATTER,
    )
    config_sub = config_parser.add_subparsers(dest="config_command")
    config_sub.required = True

    init_parser = config_sub.add_parser(
        "init",
        help="Create or update a CLI profile",
        parents=[shared],
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  printf 'app_secret' | feishu config init --profile work --app-id cli_xxx --app-secret-stdin --set-default --format json\n"
            "  feishu config init --profile staging --app-id cli_xxx --app-secret-file ./.secrets/feishu_app_secret --format json"
        ),
    )
    init_parser.add_argument("--app-secret-stdin", action="store_true", help="Read app secret from stdin")
    init_parser.add_argument("--app-secret-file", help="Read app secret from a file")
    init_parser.add_argument("--set-default", action="store_true", help="Set this profile as default")
    init_parser.set_defaults(handler=_cmd_config_init)

    show_parser = config_sub.add_parser("show", help="Show a configured profile", parents=[shared])
    show_parser.set_defaults(handler=_cmd_config_show)

    list_parser = config_sub.add_parser("list-profiles", help="List configured profiles", parents=[shared])
    list_parser.set_defaults(handler=_cmd_config_list_profiles)

    default_parser = config_sub.add_parser(
        "set-default-profile",
        help="Set the default profile",
        parents=[shared],
    )
    default_parser.add_argument("profile_name", help="Profile name to mark as default")
    default_parser.set_defaults(handler=_cmd_config_set_default_profile)

    remove_parser = config_sub.add_parser(
        "remove-profile",
        help="Remove a profile and optionally its stored app secret",
        parents=[shared],
    )
    remove_parser.add_argument(
        "profile_name",
        nargs="?",
        help="Profile name to remove, defaults to selected profile",
    )
    remove_parser.add_argument("--keep-secret", action="store_true", help="Do not delete the stored app secret")
    remove_parser.set_defaults(handler=_cmd_config_remove_profile)

    migrate_parser = config_sub.add_parser(
        "migrate-token-store",
        help="Import profiles from an existing tokens.json store",
        parents=[shared],
        formatter_class=_HELP_FORMATTER,
        epilog=(
            "Examples:\n"
            "  printf 'app_secret' | feishu config migrate-token-store --from ~/.config/feishu-bot-sdk/tokens.json --app-id cli_xxx --app-secret-stdin --format json\n"
            "  feishu config migrate-token-store --from ./tokens.json --only-profile work --default-profile work --format json"
        ),
    )
    migrate_parser.add_argument(
        "--from",
        dest="source_path",
        help="Existing token store path. Default: platform default tokens.json",
    )
    migrate_parser.add_argument(
        "--only-profile",
        dest="only_profiles",
        action="append",
        help="Import only the specified legacy token profile. Can be repeated.",
    )
    migrate_parser.add_argument(
        "--default-profile",
        help="Default profile to set after import. Default: keep current default or use imported default/first profile",
    )
    migrate_parser.add_argument("--app-secret-stdin", action="store_true", help="Read shared app secret from stdin")
    migrate_parser.add_argument("--app-secret-file", help="Read shared app secret from a file")
    migrate_parser.set_defaults(handler=_cmd_config_migrate_token_store)


__all__ = ["_build_config_commands"]
