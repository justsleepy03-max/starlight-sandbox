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

    @discord.app_commands.command(name="shop", description="View available gear and items in the shop.")
    async def shop(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🛒 Starlight RPG Shop", color=discord.Color.blue())
        
        swords_list = "\n".join([f"Tier {tid}: **{item['name'].title()}** - 🪙 {item['price']}" for tid, item in SWORDS.items()])
        armors_list = "\n".join([f"Tier {tid}: **{item['name'].title()}** - 🪙 {item['price']}" for tid, item in ARMORS.items()])
        
        embed.add_field(name="⚔️ Swords", value=swords_list, inline=False)
        embed.add_field(name="🛡️ Armor", value=armors_list, inline=False)
        embed.set_footer(text="Use /buy <sword/armor> <tier> to purchase gear!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="buy", description="Purchase items or gear from the shop.")
    @discord.app_commands.describe(category="Choose sword or armor", tier="The tier number of the item")
    async def buy(self, interaction: discord.Interaction, category: str, tier: int):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        category = category.lower()
        catalog = SWORDS if category == "sword" else ARMORS if category == "armor" else None
        
        if not catalog or tier not in catalog:
            await interaction.response.send_message("❌ Invalid category or tier! Choose `sword` or `armor` with a valid tier number.", ephemeral=True)
            return
            
        item = catalog[tier]
        if p["wallet"] < item["price"]:
            await interaction.response.send_message(f"❌ You need 🪙 {item['price']} coins to buy the **{item['name']}**, but you only have 🪙 {p['wallet']}.", ephemeral=True)
            return
            
        p["wallet"] -= item["price"]
        p["inventory"][item["name"]] = p["inventory"].get(item["name"], 0) + 1
        update_player(uid, p)
        
        await interaction.response.send_message(f"🎉 Successfully purchased **{item['name'].title()}** for 🪙 {item['price']} coins!")

    @discord.app_commands.command(name="inventory", description="Check your items, materials, and gear.")
    async def inventory(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        if not inv:
            embed.description = "Your inventory is empty! Use `/chop`, `/fish`, or visit the `/shop`."
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

    @discord.app_commands.command(name="daily", description="Claim your daily rewards!")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        bonus_coins = 500
        p["wallet"] += bonus_coins
        update_player(uid, p)
        
        await interaction.response.send_message(f"🎁 You claimed your daily reward and received **🪙 {bonus_coins} coins**!")

    @discord.app_commands.command(name="heal", description="Heal your HP back to maximum.")
    async def heal(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        p["hp"] = p["max_hp"]
        update_player(uid, p)
        
        await interaction.response.send_message(f"❤️ You used a healing potion and restored your HP to **{p['max_hp']}/{p['max_hp']}**!")

async def setup(bot):
    await bot.add_cog(RpgCog(bot))
