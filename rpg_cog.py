import discord
from discord.ext import commands
import random
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, BUNDLES

class RpgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Automatically sync global commands when the cog loads
        try:
            synced = await self.bot.tree.sync()
            print(f"Successfully synced {len(synced)} global commands from rpg_cog!")
        except Exception as e:
            print(f"Failed to sync command tree: {e}")

    # Manual prefix sync command in case global sync is delayed by Discord
    @commands.command(name="sync")
    @commands.is_owner()
    async def manual_sync(self, ctx):
        try:
            synced = await self.bot.tree.sync()
            await ctx.send(f"🔄 Successfully force-synced {len(synced)} slash commands globally!")
        except Exception as e:
            await ctx.send(f"❌ Failed to sync: {e}")

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

    @discord.app_commands.command(name="inventory", description="Check your items, materials, and Starlight bundles.")
    async def inventory(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        if not inv:
            embed.description = "Your inventory is currently empty! Visit the `/shop` or use working commands to gather items."
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

async def setup(bot):
    await bot.add_cog(RpgCog(bot))
