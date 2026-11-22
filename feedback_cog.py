import discord
from discord import app_commands
from discord.ext import commands

FEEDBACK_CHANNEL_ID = 123456789012345678  # Replace with your RVG feedback channel ID


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
      label="What happened? (Include steps or expected result)",
      style=discord.TextStyle.paragraph,
      placeholder="Describe what you did, what happened, and any error message...",
      max_length=1000,
  )

  def __init__(self, target_channel_id: int):
    super().__init__()
    self.target_channel_id = target_channel_id

  async def on_submit(self, interaction: discord.Interaction):
    channel = interaction.client.get_channel(self.target_channel_id)
    if channel is None:
      await interaction.response.send_message(
          "⚠️ Feedback channel isn't configured yet, so your note wasn't posted.",
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
      name="feedback",
      description="Submit a bug report, balance note, or suggestion for Starlight RPG.",
  )
  async def feedback(self, interaction: discord.Interaction):
    await interaction.response.send_modal(FeedbackModal(FEEDBACK_CHANNEL_ID))


async def setup(bot):
  await bot.add_cog(FeedbackCog(bot))
