import discord
from discord.ext import commands
from database import get_player, update_player

class RpgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="Test if the RPG cog is working.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("pong! RPG cog is active!")

async def setup(bot):
    await bot.add_cog(RpgCog(bot))
