import discord
from discord.ext import commands
import random
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, BUNDLES

class RpgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="Test if the RPG cog is working.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong! Starlight RPG cog is active and modular!")

    @discord.app_commands.command(name="profile", description="Check your RPG character stats, level, and gear.")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile", color=discord.Color.blurple())
        embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']} XP)\n**Area:** {p['area']}", inline=False)
        embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
        embed.add_field(name="CURRENCY", value=f"🪙 **Wallet:** {p['wallet']}\n🏛️ **Bank:** {p['bank']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="hunt", description="Hunt for monsters to gain XP and coins!")
    async def hunt(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        
        earned_coins = random.randint(15, 35) * area
        earned_xp = random.randint(10, 20) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        
        level_up_msg = ""
        if p["xp"] >= p["level"] * 100:
            p["level"] += 1
            p["xp"] = 0
            level_up_msg = f"\n🎉 **LEVEL UP!** You reached Level {p['level']}!"

        update_player(uid, p)
        
        embed = discord.Embed(title="⚔️ Hunt Completed", description=f"You fought courageously in Area {area} and won the battle!", color=discord.Color.green())
        embed.add_field(name="REWARDS", value=f"🪙 Coins: +{earned_coins}\n⭐ XP: +{earned_xp}{level_up_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="adventure", description="Embark on an epic adventure in your current area!")
    async def adventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        
        earned_coins = random.randint(50, 120) * area
        earned_xp = random.randint(40, 90) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        update_player(uid, p)
        
        embed = discord.Embed(title="🗺️ Epic Adventure", description=f"You adventured deep into the wilderness of Area {area} and triumphed over a miniboss!", color=discord.Color.orange())
        embed.add_field(name="REWARDS", value=f"🪙 Coins: +{earned_coins}\n⭐ XP: +{earned_xp}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="inventory", description="Check your items, materials, and Starlight bundles.")
    async def inventory(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        if not inv:
            embed.description = "Your inventory is currently empty! Use `/chop` or `/fish` to gather materials."
        else:
            inv_text = "\n".join([f"• **{item.title()}**: {qty}" for item, qty in inv.items()])
            embed.description = inv_text
            
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="chop", description="Chop wood in the forest for crafting materials.")
    async def chop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        wood_gained = random.randint(2, 6)
        p["inventory"]["wood"] = p["inventory"].get("wood", 0) + wood_gained
        update_player(uid, p)
        
        await interaction.response.send_message(f"🪓 You swung your axe and collected **{wood_gained}x Wood**!")

    @discord.app_commands.command(name="fish", description="Fish in the river for aquatic catches.")
    async def fish(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        fish_gained = random.randint(1, 4)
        p["inventory"]["fish"] = p["inventory"].get("fish", 0) + fish_gained
        update_player(uid, p)
        
        await interaction.response.send_message(f"🎣 You cast your line and caught **{fish_gained}x Fish**!")

    @discord.app_commands.command(name="craft", description="Craft weapons and armor using gathered materials.")
    @discord.app_commands.describe(item_type="Choose what to craft (sword or armor)")
    async def craft(self, interaction: discord.Interaction, item_type: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        
        item_type = item_type.lower()
        if item_type not in ["sword", "armor"]:
            await interaction.response.send_message("❌ You can only craft a `sword` or `armor` right now!", ephemeral=True)
            return
            
        wood_required = 10
        if inv.get("wood", 0) < wood_required:
            await interaction.response.send_message(f"❌ Crafting a {item_type} requires **{wood_required}x Wood**. Use `/chop` to gather more!", ephemeral=True)
            return
            
        inv["wood"] -= wood_required
        p["inventory"] = inv
        update_player(uid, p)
        
        await interaction.response.send_message(f"⚒️ Success! You crafted a brand new **Epic {item_type.title()}** using {wood_required}x Wood!")

async def setup(bot):
    await bot.add_cog(RpgCog(bot))
