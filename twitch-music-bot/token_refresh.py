"""
Handles automatic Twitch OAuth token refresh. When the access token
expires, this calls Twitch's token endpoint with the refresh token to
get a new access+refresh token pair, writes them back to .env so they
survive a restart, and updates the in-memory config values so the bot
can reconnect without manual intervention.
"""
import logging
import os
import re
import urllib.request
import urllib.parse
import json

import config

log = logging.getLogger("token_refresh")

TWITCH_TOKEN_URL = "https://id.twitch.tv/oauth2/token"


def refresh_token() -> str | None:
    """
    Calls Twitch's token refresh endpoint and returns the new access
    token, or None if the refresh failed. Also updates config module
    values and writes new tokens back to .env so they persist.
    """
    if not config.TWITCH_REFRESH_TOKEN or not config.TWITCH_CLIENT_ID:
        log.warning(
            "Token refresh requested but TWITCH_REFRESH_TOKEN or "
            "TWITCH_CLIENT_ID is missing from .env -- cannot auto-refresh. "
            "Add both to .env to enable persistent tokens."
        )
        return None

    log.info("Refreshing Twitch OAuth token...")

    params = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": config.TWITCH_REFRESH_TOKEN,
        "client_id": config.TWITCH_CLIENT_ID,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            TWITCH_TOKEN_URL,
            data=params,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        log.error(f"Token refresh HTTP request failed: {e}")
        return None

    new_access = data.get("access_token")
    new_refresh = data.get("refresh_token")

    if not new_access:
        log.error(f"Token refresh response missing access_token: {data}")
        return None

    log.info("Token refresh successful, writing new tokens to .env")

    # Update in-memory config so the reconnect uses the new token
    # without needing a restart
    config.TWITCH_OAUTH_TOKEN = new_access
    if new_refresh:
        config.TWITCH_REFRESH_TOKEN = new_refresh

    # Write back to .env so the new tokens survive a restart
    _update_env(new_access, new_refresh)

    return new_access


def _update_env(new_access: str, new_refresh: str | None) -> None:
    """Rewrites TWITCH_OAUTH_TOKEN and TWITCH_REFRESH_TOKEN in .env."""
    env_path = os.path.join(config.base_dir, ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(
            r"TWITCH_OAUTH_TOKEN=.*",
            f"TWITCH_OAUTH_TOKEN={new_access}",
            content,
        )
        if new_refresh:
            if "TWITCH_REFRESH_TOKEN=" in content:
                content = re.sub(
                    r"TWITCH_REFRESH_TOKEN=.*",
                    f"TWITCH_REFRESH_TOKEN={new_refresh}",
                    content,
                )
            else:
                content += f"\nTWITCH_REFRESH_TOKEN={new_refresh}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

    except OSError as e:
        log.error(f"Could not write new tokens to .env: {e}")
