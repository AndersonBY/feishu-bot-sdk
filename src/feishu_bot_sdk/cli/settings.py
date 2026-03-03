from __future__ import annotations

import argparse

DEFAULT_BASE_URL = "https://open.feishu.cn/open-apis"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_OAUTH_CALLBACK_HOST = "127.0.0.1"
DEFAULT_OAUTH_CALLBACK_PORT = 18080
DEFAULT_OAUTH_CALLBACK_PATH = "/callback"
DEFAULT_USER_TOKEN_REFRESH_BEFORE_SECONDS = 300.0
HELP_FORMATTER = argparse.RawTextHelpFormatter

ROOT_HELP_EPILOG = (
    "Quick start (Agent-friendly):\n"
    "  1) feishu auth login --scope \"offline_access contact:user:search\" --no-browser --format json\n"
    "  2) feishu auth whoami --auth-mode user --format json\n"
    "  3) feishu contact user search --query \"name\" --auth-mode user --format json\n"
    "  4) feishu calendar create-event --auth-mode user --calendar-id <id> --event-file event.json --format json\n"
    "  5) non-text message resource: feishu media download-file <resource_key> <output> "
    "--message-id <om_xxx> --resource-type image|file --auth-mode tenant --format json\n"
    "\n"
    "Token precedence: env vars > CLI flags > local token store profile."
)

AUTH_HELP_EPILOG = (
    "Common flow:\n"
    "  feishu auth login --scope \"offline_access contact:user:search calendar:calendar.event:create\" --no-browser --format json\n"
    "  feishu auth whoami --auth-mode user --format json\n"
    "  feishu auth refresh --auth-mode user --format json\n"
    "\n"
    "If login fails with redirect_uri error:\n"
    "  Configure redirect URL in Feishu console:\n"
    "  Development Config -> Security -> Redirect URL\n"
    "  Example: http://127.0.0.1:18080/callback"
)
