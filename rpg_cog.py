import discord
from discord.ext import commands
import random
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, MISC_ITEMS, BUNDLES

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

    @discord.app_commands.command(name="shop", description="View the Starlight RPG shop catalog.")
    @discord.app_commands.describe(page="Shop page number (1, 2, or 3 for Starlight Bundles)")
    async def shop(self, interaction: discord.Interaction, page: int = 1):
        if page == 1:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 1/3 (Essentials)", color=discord.Color.blue())
            embed.description = f"🌟 **STARLIGHT VENDOR:** Welcome, {interaction.user.name}! Browse our supplies and grab what you need with `/buy [item]`"
            
            items_text = (
                "🧪 **life potion** | 🪙 25\n*Restore your life with /heal*\n\n"
                "🛡️ **basic armor** | 🪙 200\n*[+2 def] An ugly armor made of wood*\n\n"
                "⚔️ **basic sword** | 🪙 150\n*[+1 at] Better than nothing huh?*\n\n"
                "🐎 **basic horse** | 🪙 500\n*[tier I] Just a normie horse*\n\n"
                "🔑 **dungeon key** | 🪙 5,000\n*You need this key to enter the /dungeon*\n\n"
                "🎫 **lottery ticket** | 🪙 50\n*To join the /lottery*\n\n"
                "🌱 **seed** | 🪙 4,000\n*Used to /farm*"
            )
            embed.add_field(name="Catalog", value=items_text, inline=False)
            
        elif page == 2:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 2/3 (Lootboxes & Boosts)", color=discord.Color.blue())
            embed.description = f"🌟 **STARLIGHT VENDOR:** High-tier gear and mysterious boxes!"
            
            items_text = (
                "📦 **common lootbox** | 🪙 800\n📦 **uncommon lootbox** | 🪙 6,000\n"
                "📦 **rare lootbox** | 🪙 40,000\n📦 **epic lootbox** | 🪙 150,000\n"
                "📦 **edgy lootbox** | 🪙 420,666\n\n"
                "✨ **life boost a** (+10 HP) | 🪙 10,000\n"
                "✨ **life boost b** (+25 HP) | 🪙 100,000\n"
                "✨ **life boost c** (+50 HP) | 🪙 1,000,000"
            )
            embed.add_field(name="Catalog", value=items_text, inline=False)
            
        else:
            embed = discord.Embed(title="✨ Starlight Shop - Page 3/3 (Exclusive Bundles)", color=discord.Color.purple())
            embed.description = f"🌟 **STARLIGHT VENDOR:** Rare custom packages crafted for our adventurers!"
            bundles_text = "\n\n".join([f"🎁 **{b_name}** | 🪙 {data['price']}\n*Contents: {', '.join(data['contents'].keys())}*" for b_name, data in BUNDLES.items()])
            embed.add_field(name="Starlight Exclusive Bundles", value=bundles_text, inline=False)
            
        embed.set_footer(text="Use /buy item_name:<name> to purchase anything!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="buy", description="Purchase items, gear, or Starlight bundles from the shop.")
    @discord.app_commands.describe(item_name="Exact name of the item or bundle you want to buy")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        item_name = item_name.lower()
        price = 0
        
        if item_name in MISC_ITEMS:
            price = MISC_ITEMS[item_name]["price"]
        elif item_name in BUNDLES:
            price = BUNDLES[item_name]["price"]
        else:
            await interaction.response.send_message(f"❌ Unknown item `{item_name}`! Check `/shop` for valid items.", ephemeral=True)
            return
            
        if p["wallet"] < price:
            await interaction.response.send_message(f"❌ You need 🪙 {price} coins to buy **{item_name}**, but you only have 🪙 {p['wallet']}.", ephemeral=True)
            return
            
        p["wallet"] -= price
        p["inventory"][item_name] = p["inventory"].get(item_name, 0) + 1
        update_player(uid, p)
        
        await interaction.response.send_message(f"🎉 Successfully purchased **{item_name.title()}** for 🪙 {price} coins!")

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
