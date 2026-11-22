import json
import os
import discord
from discord import app_commands
from discord.ext import commands

FEEDBACK_CHANNEL_ID = 123456789012345678  # Default fallback if /setfeedback hasn't been run

# Store on mounted volume if present, otherwise local working directory
DATA_DIR = (
    "/app/data"
    if os.path.isdir("/app/data")
    else ("/data" if os.path.isdir("/data") else ".")
)
CONFIG_FILE = os.path.join(DATA_DIR, "feedback_config.json")


def _load_guild_channels() -> dict[str, int]:
  if not os.path.exists(CONFIG_FILE):
    return {}
  try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
      data = json.load(f)
    return data if isinstance(data, dict) else {}
  except (OSError, json.JSONDecodeError):
    return {}


def _save_guild_channels(mapping: dict[str, int]) -> None:
  os.makedirs(os.path.dirname(CONFIG_FILE) or ".", exist_ok=True)
  with open(CONFIG_FILE, "w", encoding="utf-8") as f:
    json.dump(mapping, f, indent=2)


def get_feedback_channel_id(guild_id: int | None) -> int | None:
  if guild_id is not None:
    mapping = _load_guild_channels()
    configured = mapping.get(str(guild_id))
    if isinstance(configured, int):
      return configured
  return FEEDBACK_CHANNEL_ID if FEEDBACK_CHANNEL_ID else None


def build_feedback_embed(
    user: discord.abc.User,
    category: str,
    command_or_area: str,
    details: str,
    status: str = "Open — Logged for Review",
) -> discord.Embed:
  embed = discord.Embed(
      title="🛠️ Starlight RPG • Beta Feedback & Bug Report",
      description=(
          "Thanks for helping stress-test **V1B3** during the RVG beta! "
          "Every bug report, balance note, and edge case helps polish the engine."
      ),
      color=0x00F0FF,
      timestamp=discord.utils.utcnow(),
  )
  embed.add_field(name="📋 Type", value=category, inline=True)
  embed.add_field(
      name="📍 Command / Area",
      value=command_or_area or "Not specified",
      inline=True,
  )
  embed.add_field(name="📌 Status", value=status, inline=True)
  embed.add_field(name="📝 Details", value=details, inline=False)
  embed.set_author(
      name=f"{user.display_name} ({user.id})",
      icon_url=user.display_avatar.url if user.display_avatar else None,
  )
  embed.set_footer(
      text="Rebel Vibez Gaming • Starlight RPG (V1B3) Beta • Attach screenshots if needed"
  )
  return embed


class FeedbackModal(discord.ui.Modal, title="Starlight RPG Beta Feedback"):
  report_type = discord.ui.TextInput(
      label="Type (Bug / Balance / Idea)",
      placeholder="Bug Report, Loot/Economy Balance, UI/Command Idea...",
      max_length=50,
  )
  location = discord.ui.TextInput(
      label="Command, Area, or Item Involved",
      placeholder="e.g. /open, /claimbiomequest, Glimmering Meadows, Uncommon Lootbox",
      required=False,
      max_length=100,
  )
  details = discord.ui.TextInput(
      label="What happened? (Steps & expected result)",
      style=discord.TextStyle.paragraph,
      placeholder="Describe what you did, what happened, and any error message...",
      max_length=1000,
  )

  def __init__(self, target_channel_id: int | None):
    super().__init__()
    self.target_channel_id = target_channel_id

  async def on_submit(self, interaction: discord.Interaction):
    if not self.target_channel_id:
      await interaction.response.send_message(
          "⚠️ No feedback channel is set yet. An admin can run `/setfeedback` first.",
          ephemeral=True,
      )
      return

    channel = interaction.client.get_channel(self.target_channel_id)
    if channel is None:
      try:
        channel = await interaction.client.fetch_channel(self.target_channel_id)
      except discord.HTTPException:
        channel = None

    if channel is None:
      await interaction.response.send_message(
          "⚠️ Configured feedback channel wasn't found. Ask an admin to update it with `/setfeedback`.",
          ephemeral=True,
      )
      return

    embed = build_feedback_embed(
        user=interaction.user,
        category=self.report_type.value.strip(),
        command_or_area=self.location.value.strip() or "General / Unspecified",
        details=self.details.value.strip(),
    )
    await channel.send(embed=embed)
    await interaction.response.send_message(
        "✅ Your feedback has been logged for the Starlight RPG beta!",
        ephemeral=True,
    )


class FeedbackCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(
      name="setfeedback",
      description="Set the channel where /feedback reports are sent (Admin only).",
  )
  @app_commands.describe(
      channel="Select the text channel for Starlight RPG feedback reports"
  )
  @app_commands.default_permissions(manage_guild=True)
  async def setfeedback(
      self, interaction: discord.Interaction, channel: discord.TextChannel
  ):
    if interaction.guild_id is None:
      await interaction.response.send_message(
          "❌ `/setfeedback` can only be used inside a server.",
          ephemeral=True,
      )
      return

    mapping = _load_guild_channels()
    mapping[str(interaction.guild_id)] = channel.id
    _save_guild_channels(mapping)

    await interaction.response.send_message(
        f"✅ Feedback channel set to {channel.mention} for this server!",
        ephemeral=True,
    )

  @app_commands.command(
      name="feedback",
      description="Submit a bug report, balance note, or suggestion for Starlight RPG.",
  )
  async def feedback(self, interaction: discord.Interaction):
    channel_id = get_feedback_channel_id(interaction.guild_id)
    await interaction.response.send_modal(FeedbackModal(channel_id))


async def setup(bot):
  await bot.add_cog(FeedbackCog(bot))
