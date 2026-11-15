import discord
from discord.ext import commands

class QuestsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="questboard", description="View available active side quests!")
    async def questboard(self, interaction: discord.Interaction):
        player_area = 1  # Placeholder for database lookup

        embed = discord.Embed(
            title="📜 Starlight Quest Board",
            description=f"*Current Unlocked Area Tier: {player_area}*\n\nHere are the quests available for your progression:\n",
            color=discord.Color.gold()
        )

        # Quest 1: Area 1 requirement
        if player_area >= 1:
            embed.add_field(name="", value="✅ **Goblin Woods Patrol** (Rank: F) — *Available*", inline=False)
        else:
            embed.add_field(name="", value="🔒 ~~**Goblin Woods Patrol**~~ (Rank: F) — *Requires Area 1*", inline=False)

        # Quest 2: Area 5 requirement (Crystal Caverns / Mining unlock)
        if player_area >= 5:
            embed.add_field(name="", value="✅ **The Crystal Cavern Run** (Rank: E) — *Available*", inline=False)
        else:
            embed.add_field(name="", value="🔒 ~~**The Crystal Cavern Run**~~ (Rank: E) — *Requires Area 5*", inline=False)

        # Quest 3: Area 10 requirement
        if player_area >= 10:
            embed.add_field(name="", value="✅ **Dragon's Peak Ascend** (Rank: A) — *Available*", inline=False)
        else:
            embed.add_field(name="", value="🔒 ~~**Dragon's Peak Ascend**~~ (Rank: A) — *Requires Area 10*", inline=False)

        embed.set_footer(text="Use /quest accept <name> to take on an unlocked quest!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(QuestsCog(bot))
