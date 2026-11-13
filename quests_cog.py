import discord
from discord.ext import commands

class QuestsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="questboard", description="View available active side quests!")
    async def questboard(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📜 Starlight Quest Board",
            description="Here are the active quests available for your party:\n\n• **Goblin Woods Patrol** (Rank: F)\n• **The Crystal Cavern Run** (Rank: E)\n• **Dragon's Peak Ascend** (Rank: A)",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Use /quest accept <name> to take on a quest!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(QuestsCog(bot))
