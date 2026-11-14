import discord
from discord.ext import commands

class QuestsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Define quests with their required minimum unlocked area
        self.quest_pool = [
            {"name": "Goblin Woods Patrol", "rank": "F", "min_area": 1, "desc": "Secure the perimeter."},
            {"name": "The Crystal Cavern Run", "rank": "E", "min_area": 5, "desc": "Mine 10 Iron Ore & gather crystals."},
            {"name": "Dragon's Peak Ascend", "rank": "A", "min_area": 10, "desc": "Scale the dangerous heights."}
        ]

    @discord.app_commands.command(name="questboard", description="View available active side quests!")
    async def questboard(self, interaction: discord.Interaction):
        # Temporary placeholder for player area tier
        player_area = 1  # This will check your database once integrated!

        embed = discord.Embed(
            title="📜 Starlight Quest Board",
            description=f"*Current Unlocked Area Tier: {player_area}*\n\nHere are the quests available for your progression:\n",
            color=discord.Color.gold()
        ]

        for q in self.quest_pool:
            if player_area >= q["min_area"]:
                status = f"✅ **{q['name']}** (Rank: {q['rank']}) — *Available*"
            else:
                status = f"🔒 ~~**{q['name']}**~~ (Rank: {q['rank']}) — *Requires Area {q['min_area']}*"
            
            embed.add_field(name="", value=status, inline=False)

        embed.set_footer(text="Use /quest accept <name> to take on an unlocked quest!")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(QuestsCog(bot))
