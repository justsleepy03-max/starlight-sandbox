import time
import discord
from discord import app_commands
from discord.ext import commands

# Default cooldown (in seconds) applied to every slash command not listed below
DEFAULT_COOLDOWN_SECONDS = 8.0

# Optional per-command overrides (use qualified command name, e.g. "hunt" or "economy shop")
CUSTOM_COOLDOWNS: dict[str, float] = {
    "big_arena": 15.0,
    "minintboss": 15.0,
    "hunt_hardmode": 15.0,
    "adventure_hardmode": 15.0,
    "casino": 12.0,
    "multidice": 12.0,
    "big_dice": 12.0,
    "wheel": 12.0,
}

# Read-only / menu commands that stay instant with no cooldown
EXEMPT_COMMANDS: set[str] = {
    "help",
    "profile",
    "stats",
    "bag",
    "inventory",
    "pets",
    "incubator",
    "expedition-status",
    "badge",
    "leaderboard",
}


class CooldownCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Maps (user_id, qualified_command_name) -> monotonic expiry timestamp
        self._cooldowns: dict[tuple[int, str], float] = {}
        self._last_cleanup = time.monotonic()

        # Hook into the bot's global app_command tree check
        self._previous_interaction_check = bot.tree.interaction_check
        bot.tree.interaction_check = self._global_slash_cooldown

    async def cog_unload(self) -> None:
        # Restore previous tree check cleanly if this cog is unloaded/reloaded
        self.bot.tree.interaction_check = self._previous_interaction_check

    def _cleanup_expired(self, now: float) -> None:
        # Periodically prune expired entries so memory stays flat
        if now - self._last_cleanup < 300.0:
            return
        self._cooldowns = {k: exp for k, exp in self._cooldowns.items() if exp > now}
        self._last_cleanup = now

    async def _global_slash_cooldown(self, interaction: discord.Interaction) -> bool:
        # Run any pre-existing tree check first if one was registered
        if self._previous_interaction_check is not None:
            allowed = await self._previous_interaction_check(interaction)
            if not allowed:
                return False

        # Only rate-limit slash commands (ignore autocomplete, buttons, select menus)
        if interaction.type is not discord.InteractionType.application_command:
            return True

        command = interaction.command
        if command is None:
            return True

        cmd_name = command.qualified_name
        if cmd_name in EXEMPT_COMMANDS:
            return True

        duration = CUSTOM_COOLDOWNS.get(cmd_name, DEFAULT_COOLDOWN_SECONDS)
        if duration <= 0:
            return True

        now = time.monotonic()
        self._cleanup_expired(now)

        key = (interaction.user.id, cmd_name)
        expires_at = self._cooldowns.get(key, 0.0)

        if now < expires_at:
            remaining = max(0.1, expires_at - now)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"⏳ Slow down! Please wait **{remaining:.1f}s** before using `/{cmd_name}` again.",
                    ephemeral=True,
                )
            return False

        self._cooldowns[key] = now + duration
        return True


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CooldownCog(bot))
