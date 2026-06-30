"""
Lets the streamer rename commands without editing code -- useful once a
bot has enough commands that some names start colliding with other bots
or feel too generic (e.g. !skip is an extremely common bot command name).

command_aliases.txt format, one per line:
    original_command=new_name

Example:
    sr=songreq
    skip=voteskip

Once an alias is set for a command, the ORIGINAL name stops working
entirely -- !sr would no longer do anything once sr=songreq is active,
only !songreq would. This is intentional: it avoids the confusing
situation of two different names doing the same thing, and means mods
who only know the new name aren't surprised that the old one still works
for everyone else.

Lines starting with # are treated as comments and ignored. The file is
optional -- if it doesn't exist, no aliasing happens and all commands
work under their original names exactly as before.
"""
import logging
import os

log = logging.getLogger("command_aliases")

ALIASES_FILENAME = "command_aliases.txt"


class CommandAliases:
    def __init__(self, base_dir: str):
        self.path = os.path.join(base_dir, ALIASES_FILENAME)
        # original_command -> alias
        self._alias_for: dict[str, str] = {}
        # alias -> original_command (the reverse lookup actually used to
        # rewrite incoming messages, since chat sends the alias and we
        # need to find which real command it maps back to)
        self._original_for: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Re-reads command_aliases.txt from disk. Safe to call anytime,
        including while the bot is running -- e.g. from a !reloadaliases
        command, without needing a restart."""
        self._alias_for = {}
        self._original_for = {}

        if not os.path.exists(self.path):
            log.info(f"No {ALIASES_FILENAME} found, all commands use their original names")
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError as e:
            log.warning(f"Could not read {ALIASES_FILENAME}: {e}")
            return

        for lineno, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                log.warning(f"{ALIASES_FILENAME} line {lineno}: missing '=', ignoring: {line!r}")
                continue
            original, _, alias = line.partition("=")
            original = original.strip().lstrip("!").lower()
            alias = alias.strip().lstrip("!").lower()
            if not original or not alias:
                log.warning(f"{ALIASES_FILENAME} line {lineno}: empty command or alias, ignoring: {line!r}")
                continue
            if alias in self._original_for:
                log.warning(
                    f"{ALIASES_FILENAME} line {lineno}: alias '{alias}' is already used for "
                    f"'{self._original_for[alias]}', ignoring this duplicate"
                )
                continue
            self._alias_for[original] = alias
            self._original_for[alias] = original

        if self._alias_for:
            log.info(f"Loaded {len(self._alias_for)} command alias(es): {self._alias_for}")

    def rewrite_command_name(self, name: str) -> str | None:
        """
        Given the command name a chat message is trying to invoke (without
        the ! prefix), returns the actual command name that should run, or
        None if this name should NOT run at all.

        - If `name` is a command that has an alias set, and the chatter
          used the OLD name, that's now blocked -- returns None.
        - If `name` IS an alias for some other command, returns the real
          underlying command name to actually run.
        - Otherwise (no alias involved at all), returns `name` unchanged.
        """
        if name in self._alias_for:
            # someone typed the original name, but an alias is active --
            # block the original name entirely
            return None
        if name in self._original_for:
            # someone typed the alias -- resolve to the real command
            return self._original_for[name]
        return name

    def alias_for(self, original_command: str) -> str | None:
        """Returns the active alias for a command, or None if unaliased."""
        return self._alias_for.get(original_command)
