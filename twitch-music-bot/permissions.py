"""
Decides whether a given chatter is allowed to run a given command right now,
based on config.PERMISSIONS (role level) and config.COOLDOWNS (per-command timing).
"""
import time

import config


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

    def user_level(self, username: str, is_mod: bool, is_sub: bool, is_broadcaster: bool) -> str:
        if is_broadcaster or username.lower() == config.TWITCH_BROADCASTER_USERNAME:
            return "broadcaster"
        if is_mod:
            return "moderator"
        if is_sub:
            return "subscriber"
        return "everyone"

    def check_permission(self, command: str, user_level: str) -> None:
        required = config.PERMISSIONS.get(command, "everyone")
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
