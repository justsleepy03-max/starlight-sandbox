import discord
from discord.ext import commands
import random
from database import get_player, update_player

# 24/7 Rotating Quest Pool
QUEST_POOL = [
    {"id": "hunt_monsters", "title": "Monster Slayer", "desc": "Hunt 5 times in the wild", "target": 5, "type": "hunt", "reward_coins": 1000, "reward_xp": 500},
    {"id": "gather_wood", "title": "Lumberjack Duty", "desc": "Chop wood 4 times", "target": 4, "type": "chop", "reward_coins": 800, "reward_xp": 400},
    {"id": "catch_fish", "title": "Master Angler", "desc": "Fish in the river 4 times", "target": 4, "type": "fish", "reward_coins": 800, "reward_xp": 400},
]

class QuestsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="quest", description="Check your current active Starlight quest or take a new one.")
    async def quest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        if "active_quest" not in p:
            p["active_quest"] = None

        active = p["active_quest"]
        
        # If no active quest, assign a fresh rotating task from the pool
        if not active:
            selected = random.choice(QUEST_POOL)
            p["active_quest"] = {
                "id": selected["id"],
                "title": selected["title"],
                "desc": selected["desc"],
                "type": selected["type"],
                "progress": 0,
                "target": selected["target"],
                "reward_coins": selected["reward_coins"],
                "reward_xp": selected["reward_xp"]
            }
            update_player(uid, p)
            active = p["active_quest"]

        embed = discord.Embed(title="📜 Active Starlight Quest", color=discord.Color.gold())
        embed.add_field(
            name=active["title"], 
            value=f"*{active['desc']}*\n\n**Progress:** {active['progress']}/{active['target']}\n**Rewards:** 🪙 {active['reward_coins']} coins | ⭐ {active['reward_xp']} XP", 
            inline=False
        )
        
        if active["progress"] >= active["target"]:
            embed.set_footer(text="✨ Quest completed! Use /claimquest to collect your rewards!")
        else:
            embed.set_footer(text="🔒 Locked: Complete this quest before taking a new one.")
            
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="claimquest", description="Claim your rewards for completing your active quest.")
    async def claimquest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        active = p.get("active_quest")
        if not active:
            await interaction.response.send_message("❌ You don't have an active quest! Use `/quest` to get one.", ephemeral=True)
            return
            
        if active["progress"] < active["target"]:
            await interaction.response.send_message(f"❌ Quest incomplete! ({active['progress']}/{active['target']}). Keep working on it!", ephemeral=True)
            return
            
        # Deliver rewards
        p["wallet"] += active["reward_coins"]
        p["xp"] += active["reward_xp"]
        
        # Clear active quest so they can roll a new one via /quest
        p["active_quest"] = None
        update_player(uid, p)
        
        await interaction.response.send_message(f"🎉 **Quest Completed!** You received 🪙 **{active['reward_coins']} coins** and ⭐ **{active['reward_xp']} XP**! Use `/quest` to take your next task.")

async def setup(bot):
    await bot.add_cog(QuestsCog(bot))
