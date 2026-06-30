"""
Decides whether a given chatter is allowed to run a given command right now,
based on config.PERMISSIONS (role level) and config.COOLDOWNS (per-command timing).

Permission levels can also be changed at runtime via !setperm (mod/broadcaster
only) without restarting the bot or recompiling -- overrides are persisted to
permission_overrides.json so they survive a restart too. config.PERMISSIONS
is still the default for any command that's never been overridden.
"""
import json
import logging
import os
import time

import config

log = logging.getLogger("permissions")

OVERRIDES_PATH = os.path.join(config.base_dir, "permission_overrides.json")


class PermissionDenied(Exception):
    def __init__(self, required_level: str):
        self.required_level = required_level
        super().__init__(f"requires {required_level} or higher")


class OnCooldown(Exception):
    def __init__(self, seconds_left: float):
        self.seconds_left = seconds_left
        super().__init__(f"{seconds_left:.0f}s left")


class PermissionManager:
    def __init__(self):
        # cooldowns[command][username] = last_used_timestamp
        self._cooldowns: dict[str, dict[str, float]] = {}
        # runtime overrides, loaded from disk -- takes precedence over
        # config.PERMISSIONS for any command present here
        self._overrides: dict[str, str] = self._load_overrides()

    def _load_overrides(self) -> dict[str, str]:
        if not os.path.exists(OVERRIDES_PATH):
            return {}
        try:
            with open(OVERRIDES_PATH, "r") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                log.warning("permission_overrides.json did not contain a JSON object, ignoring it")
                return {}
            return data
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Could not load permission_overrides.json: {e}")
            return {}

    def _save_overrides(self) -> None:
        try:
            with open(OVERRIDES_PATH, "w") as f:
                json.dump(self._overrides, f, indent=2)
        except OSError as e:
            log.warning(f"Could not save permission_overrides.json: {e}")

    def set_permission(self, command: str, level: str) -> None:
        """Changes a command's required level at runtime, persisted to disk."""
        if level not in config.LEVEL_RANK:
            raise ValueError(f"'{level}' is not a valid level (expected one of: {', '.join(config.LEVEL_RANK)})")
        self._overrides[command] = level
        self._save_overrides()

    def get_permission(self, command: str) -> str:
        """Returns the currently effective required level for a command,
        whether from a runtime override or the config.py default."""
        return self._overrides.get(command, config.PERMISSIONS.get(command, "everyone"))

    def user_level(self, username: str, is_mod: bool, is_sub: bool, is_broadcaster: bool) -> str:
        if is_broadcaster or username.lower() == config.TWITCH_BROADCASTER_USERNAME:
            return "broadcaster"
        if is_mod:
            return "moderator"
        if is_sub:
            return "subscriber"
        return "everyone"

    def check_permission(self, command: str, user_level: str) -> None:
        required = self.get_permission(command)
        if config.LEVEL_RANK.index(user_level) < config.LEVEL_RANK.index(required):
            raise PermissionDenied(required)

    def check_cooldown(self, command: str, username: str) -> None:
        cooldown = config.COOLDOWNS.get(command, 0)
        if cooldown <= 0:
            return
        username = username.lower()
        last_used = self._cooldowns.get(command, {}).get(username)
        if last_used is not None:
            elapsed = time.time() - last_used
            if elapsed < cooldown:
                raise OnCooldown(cooldown - elapsed)

    def record_use(self, command: str, username: str) -> None:
        self._cooldowns.setdefault(command, {})[username.lower()] = time.time()
