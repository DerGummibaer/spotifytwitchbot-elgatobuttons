"""
The Twitch chat bot. Each !command is a method below. Permission and
cooldown checks happen first, in a consistent way, via permissions.py.

This bot does not talk to Spotify directly -- every command sends a
command to the always-on Spotify service over the local socket, exactly
the way the Stream Deck plugin does. If the service isn't running, chat
commands fail gracefully with a message rather than crashing the bot.
"""
import asyncio
import logging

from twitchio.ext import commands

import config
from command_aliases import CommandAliases
from permissions import PermissionManager, PermissionDenied, OnCooldown
from request_tracker import RequestTracker
from service_client import send_command, ServiceUnavailable
from token_refresh import refresh_token

log = logging.getLogger("twitch_bot")

SKIP_POLL_INTERVAL = 5  # seconds between now-playing checks for auto-skip

# Loaded once at import time -- BEFORE the class body below, since
# @commands.command(name=...) decorator arguments are evaluated when the
# class is defined, not at runtime per-message. This is also why aliases
# only take effect after restarting the bot: editing command_aliases.txt
# while the bot is running doesn't change a decorator that already ran.
#
# The actual mechanism: when an alias IS set for a command (e.g.
# sr=songreq), we register the command under name="songreq" instead of
# name="sr" -- NOT as name="sr", aliases=["songreq"]. twitchio then never
# learns "sr" exists as a trigger at all once aliased, which is exactly
# "the original command should not work if an alias has been set"
# without needing any runtime detection of which name was typed (which
# turned out to be unreliable to determine cleanly from inside a command
# body -- see command_aliases.py for the full reasoning).
_aliases = CommandAliases(config.base_dir)


def _effective_name(original: str) -> str:
    """Returns the alias for a command if one is set, otherwise the
    original name unchanged -- use this as the name= for every
    @commands.command decorator below instead of hardcoding the name."""
    return _aliases.alias_for(original) or original


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config.TWITCH_OAUTH_TOKEN,
            prefix="!",
            initial_channels=[config.TWITCH_CHANNEL],
        )
        self.tracker = RequestTracker()
        self.perms = PermissionManager()
        self._skip_poll_task = None

    async def event_ready(self):
        log.info(f"Logged in as {self.nick}, joined #{config.TWITCH_CHANNEL}")
        self._skip_poll_task = asyncio.create_task(self._auto_skip_poll())

    async def event_token_expired(self):
        """
        Called by twitchio when an API call returns 401 (token expired).
        Returns a new access token to reconnect with, or None to let
        twitchio try its own token generation. Automatically updates
        .env with the new tokens so they persist across restarts.
        """
        log.warning("Twitch token expired -- attempting automatic refresh...")
        new_token = refresh_token()
        if new_token:
            log.info("Token refresh successful, reconnecting...")
            return new_token
        log.error(
            "Token refresh failed -- bot will disconnect. "
            "Regenerate tokens at twitchtokengenerator.com and update .env, "
            "then restart the bot."
        )
        return None

    async def event_message(self, message):
        # Override the default event_message to ensure commands work even
        # when the bot account and the broadcaster account are the same
        # Twitch account -- twitchio's default behavior filters out
        # messages in ways that silently break this common single-account
        # setup. Passing all messages directly to handle_commands lets
        # twitchio's command parser decide what to do with them.
        if message.echo:
            return
        await self.handle_commands(message)

    async def close(self):
        if self._skip_poll_task:
            self._skip_poll_task.cancel()
        await super().close()

    async def _auto_skip_poll(self):
        """
        Polls now-playing every few seconds. If the current track was !removed,
        sends a skip command automatically. This works around Spotify's API not
        supporting removal of items from the queue.
        """
        while True:
            await asyncio.sleep(SKIP_POLL_INTERVAL)
            try:
                result = await send_command({"action": "now_playing"})
                uri = result.get("uri")
                if uri and self.tracker.should_skip(uri):
                    log.info(f"Auto-skipping removed track: {result.get('track')} ({uri})")
                    self.tracker.clear_skip(uri)
                    await send_command({"action": "skip"})
            except ServiceUnavailable:
                pass  # Spotify service not running, try again next poll
            except Exception as e:
                # repr() rather than str() ensures the exception TYPE is
                # always visible even when the exception has no message --
                # some asyncio/network exceptions raise with an empty str()
                # which previously logged as "Auto-skip poll error: " with
                # nothing after the colon, making it impossible to diagnose
                log.warning(f"Auto-skip poll error: {repr(e)}")

    def _user_level(self, ctx: commands.Context) -> str:
        badges = ctx.author.badges or {}
        is_mod = ctx.author.is_mod
        is_sub = "subscriber" in badges or "founder" in badges
        is_broadcaster = "broadcaster" in badges
        return self.perms.user_level(ctx.author.name, is_mod, is_sub, is_broadcaster)

    async def _guard(self, ctx: commands.Context, command: str) -> bool:
        """Runs permission + cooldown checks. Sends a chat message and returns
        False if the command should not proceed.

        `command` is always the ORIGINAL internal name (e.g. "sr"), used
        for permission/cooldown lookups regardless of aliasing -- but
        user-facing messages show the actual current trigger name (which
        could be an alias like "songreq"), so the error makes sense to
        whoever's reading it in chat."""
        display_name = _effective_name(command)
        level = self._user_level(ctx)
        try:
            self.perms.check_permission(command, level)
            self.perms.check_cooldown(command, ctx.author.name)
        except PermissionDenied as e:
            await ctx.send(f"@{ctx.author.name} sorry, !{display_name} needs {e.required_level} or higher.")
            return False
        except OnCooldown as e:
            await ctx.send(f"@{ctx.author.name} !{display_name} is on cooldown, try again in {e.seconds_left:.0f}s.")
            return False
        self.perms.record_use(command, ctx.author.name)
        return True

    @commands.command(name=_effective_name("sr"))
    async def song_request(self, ctx: commands.Context, *, query: str = ""):
        if not await self._guard(ctx, "sr"):
            return
        if not query.strip():
            await ctx.send(f"@{ctx.author.name} usage: !{_effective_name('sr')} <song name or Spotify link>")
            return
        if self.tracker.count_pending_for(ctx.author.name) >= config.MAX_QUEUE_PER_USER:
            await ctx.send(
                f"@{ctx.author.name} you already have {config.MAX_QUEUE_PER_USER} songs queued, "
                f"use !{_effective_name('remove')} first if you want to swap one."
            )
            return

        try:
            result = await send_command({"action": "queue_add", "query": query})
        except ServiceUnavailable:
            await ctx.send(f"@{ctx.author.name} the Spotify service isn't running right now.")
            return

        if not result.get("ok"):
            if result.get("error") == "launching_spotify":
                await ctx.send(
                    f"@{ctx.author.name} Spotify wasn't running, so it's starting now -- "
                    f"try your request again in a few seconds!"
                )
            else:
                await ctx.send(f"@{ctx.author.name} couldn't find or queue that song. Is Spotify playing?")
            return

        self.tracker.add(ctx.author.name, result["uri"], result["name"], result["artist"])
        await ctx.send(f"@{ctx.author.name} added {result['name']} by {result['artist']} to the queue!")

    @commands.command(name=_effective_name("remove"))
    async def remove_request(self, ctx: commands.Context):
        if not await self._guard(ctx, "remove"):
            return
        last = self.tracker.last_pending_for(ctx.author.name)
        if last is None:
            await ctx.send(f"@{ctx.author.name} you don't have any pending requests to remove.")
            return
        self.tracker.mark_removed(last)
        await ctx.send(
            f"@{ctx.author.name} removed {last.track_name} from the queue -- "
            f"it will be skipped automatically if it comes up."
        )

    @commands.command(name=_effective_name("vol"))
    async def volume(self, ctx: commands.Context, *, amount: str = ""):
        if not await self._guard(ctx, "vol"):
            return
        amount = amount.strip()

        try:
            if not amount:
                result = await send_command({"action": "get_volume"})
                if result.get("ok"):
                    await ctx.send(f"Current volume is {result['volume']}%")
                else:
                    await ctx.send("Couldn't read the current volume. Is Spotify playing?")
                return

            try:
                value = int(amount)
            except ValueError:
                await ctx.send(f"@{ctx.author.name} usage: !{_effective_name('vol')} <0-100>")
                return
            if not (0 <= value <= 100):
                await ctx.send(f"@{ctx.author.name} volume must be between 0 and 100.")
                return

            result = await send_command({"action": "vol_set", "value": value})
            if result.get("ok"):
                await ctx.send(f"Volume set to {value}%")
            elif result.get("error") == "launching_spotify":
                await ctx.send("Spotify wasn't running, so it's starting now -- try again in a few seconds!")
            else:
                await ctx.send("Couldn't set volume. Is Spotify playing?")
        except ServiceUnavailable:
            await ctx.send(f"@{ctx.author.name} the Spotify service isn't running right now.")

    @commands.command(name=_effective_name("skip"))
    async def skip_song(self, ctx: commands.Context):
        if not await self._guard(ctx, "skip"):
            return
        try:
            result = await send_command({"action": "skip"})
        except ServiceUnavailable:
            await ctx.send(f"@{ctx.author.name} the Spotify service isn't running right now.")
            return
        if result.get("ok"):
            await ctx.send(f"@{ctx.author.name} skipped the current song.")
        elif result.get("error") == "launching_spotify":
            await ctx.send(f"@{ctx.author.name} Spotify wasn't running, so it's starting now -- try again in a few seconds!")
        else:
            await ctx.send("Couldn't skip. Is Spotify playing?")

    @commands.command(name=_effective_name("sq"))
    async def show_queue(self, ctx: commands.Context):
        if not await self._guard(ctx, "sq"):
            return
        try:
            result = await send_command({"action": "get_queue", "limit": 5})
        except ServiceUnavailable:
            await ctx.send(f"@{ctx.author.name} the Spotify service isn't running right now.")
            return
        queue = result.get("queue", [])
        if not queue:
            await ctx.send("The queue is empty.")
            return
        listing = " | ".join(f"{t['name']} - {t['artist']}" for t in queue)
        await ctx.send(f"Up next: {listing}")

    @commands.command(name=_effective_name("song"))
    async def current_song(self, ctx: commands.Context):
        if not await self._guard(ctx, "song"):
            return
        try:
            result = await send_command({"action": "now_playing"})
        except ServiceUnavailable:
            await ctx.send(f"@{ctx.author.name} the Spotify service isn't running right now.")
            return
        if not result.get("ok") or not result.get("track"):
            await ctx.send("Nothing is playing right now.")
            return
        track = result["track"]
        artist = result.get("artist", "Unknown artist")
        if result.get("is_playing"):
            await ctx.send(f"Now playing: {track} - {artist}")
        else:
            await ctx.send(f"Paused: {track} - {artist}")

    @commands.command(name="setperm")
    async def set_permission(self, ctx: commands.Context, *, args: str = ""):
        # Hardcoded to moderator, NOT routed through self._guard/the
        # overridable permission system -- if this were itself
        # overridable, a streamer could accidentally lock themselves out
        # of ever changing permissions again with a typo.
        level = self._user_level(ctx)
        if config.LEVEL_RANK.index(level) < config.LEVEL_RANK.index("moderator"):
            await ctx.send(f"@{ctx.author.name} !setperm is mod-only.")
            return

        parts = args.split()
        if len(parts) != 2:
            await ctx.send(
                f"@{ctx.author.name} usage: !setperm <command> <level> "
                f"-- e.g. !setperm skip moderator. Levels: {', '.join(config.LEVEL_RANK)}"
            )
            return

        command_name, new_level = parts[0].lstrip("!").lower(), parts[1].lower()
        if command_name not in config.PERMISSIONS:
            await ctx.send(
                f"@{ctx.author.name} unknown command '{command_name}'. "
                f"Known commands: {', '.join(config.PERMISSIONS.keys())}"
            )
            return

        try:
            self.perms.set_permission(command_name, new_level)
        except ValueError as e:
            await ctx.send(f"@{ctx.author.name} {e}")
            return

        await ctx.send(f"!{command_name} now requires {new_level} or higher.")

    @commands.command(name="perms")
    async def show_permissions(self, ctx: commands.Context):
        level = self._user_level(ctx)
        if config.LEVEL_RANK.index(level) < config.LEVEL_RANK.index("moderator"):
            await ctx.send(f"@{ctx.author.name} !perms is mod-only.")
            return
        listing = " | ".join(
            f"!{cmd}: {self.perms.get_permission(cmd)}" for cmd in config.PERMISSIONS.keys()
        )
        await ctx.send(listing)
