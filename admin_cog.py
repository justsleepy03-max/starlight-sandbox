import os
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from database import wipe_all_players, wipe_single_player

# Optional: add extra Discord user IDs as strings here if needed (e.g., {"123456789012345678"})
EXTRA_OWNER_IDS: set[str] = set()


async def _is_bot_admin(interaction: discord.Interaction) -> bool:
    user_id = str(interaction.user.id)
    if user_id in EXTRA_OWNER_IDS:
        return True
    if interaction.client and hasattr(interaction.client, "is_owner"):
        try:
            return await interaction.client.is_owner(interaction.user)
        except Exception:
            return False
    return False


class WipeConfirmView(discord.ui.View):
    def __init__(self, invoker_id: str, target_user: Optional[discord.User] = None):
        super().__init__(timeout=30)
        self.invoker_id = invoker_id
        self.target_user = target_user
        self.resolved = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.invoker_id:
            await interaction.response.send_message(
                "❌ Only the admin who ran `/wipe` can confirm or cancel this action.",
                ephemeral=True
            )
            return False
        if not await _is_bot_admin(interaction):
            await interaction.response.send_message(
                "❌ You do not have permission to execute this wipe.",
                ephemeral=True
            )
            return False
        return True

    def _disable_all(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    @discord.ui.button(label="⚠️ Confirm Wipe", style=discord.ButtonStyle.danger)
    async def confirm_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.resolved = True
        self._disable_all()

        if self.target_user is not None:
            found, backup_path = wipe_single_player(self.target_user.id)
            backup_name = os.path.basename(backup_path) if backup_path else "No prior data file found"

            if found:
                desc = (
                    f"**{self.target_user.mention}**'s profile has been reset to clean starter defaults.\n\n"
                    f"🎯 **Target Reset:** `{self.target_user}` (`{self.target_user.id}`)\n"
                    f"💾 **Pre-Wipe Backup:** `{backup_name}`"
                )
            else:
                desc = (
                    f"No saved profile was found for **{self.target_user.mention}** (`{self.target_user.id}`), so no data was altered.\n\n"
                    f"💾 **Pre-Wipe Backup:** `{backup_name}`"
                )

            embed = discord.Embed(
                title="🧹 Single-Player Wipe Complete",
                description=desc,
                color=discord.Color.green()
            )
        else:
            wiped_count, backup_path = wipe_all_players()
            backup_name = os.path.basename(backup_path) if backup_path else "No prior data file found"

            embed = discord.Embed(
                title="🧹 Server Wipe Complete — Fresh Start!",
                description=(
                    "All player profiles have been reset to clean starter defaults.\n\n"
                    f"👥 **Profiles Reset:** `{wiped_count}`\n"
                    f"💾 **Pre-Wipe Backup:** `{backup_name}`"
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text="Starlight RPG • Happy New Year!")

        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_wipe(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.resolved = True
        self._disable_all()

        embed = discord.Embed(
            title="🛑 Wipe Cancelled",
            description="No player profiles or economy stats were modified.",
            color=discord.Color.blurple()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    async def on_timeout(self):
        if not self.resolved:
            self._disable_all()


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="wipe", description="Admin only: Backup and reset a specific player or all player profiles.")
    @app_commands.describe(target="Optional user to wipe individually (leave empty to wipe everyone)")
    async def wipe(self, interaction: discord.Interaction, target: Optional[discord.User] = None):
        if not await _is_bot_admin(interaction):
            return await interaction.response.send_message(
                "❌ This command is restricted to the bot owner/admin.",
                ephemeral=True
            )

        if target is not None:
            warning_embed = discord.Embed(
                title="⚠️ Confirm Single-Player Wipe",
                description=(
                    f"This will **reset {target.mention}**'s profile (coins, levels, XP, inventory, gear, quests, and Spire/NG+ progress) "
                    "back to starter defaults.\n\n"
                    "Other players' data will stay untouched, and a timestamped backup will be saved automatically first.\n"
                    "*You have **30 seconds** to confirm or cancel.*"
                ),
                color=discord.Color.orange()
            )
        else:
            warning_embed = discord.Embed(
                title="⚠️ Confirm Full Starlight RPG Wipe",
                description=(
                    "This will **reset every player's profile** (coins, levels, XP, inventory, gear, quests, and Spire/NG+ progress) "
                    "back to starter defaults.\n\n"
                    "A timestamped backup will be saved automatically before the wipe runs.\n"
                    "*You have **30 seconds** to confirm or cancel.*"
                ),
                color=discord.Color.red()
            )

        view = WipeConfirmView(invoker_id=str(interaction.user.id), target_user=target)
        await interaction.response.send_message(embed=warning_embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
