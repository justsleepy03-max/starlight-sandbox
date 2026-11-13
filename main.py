import asyncio
import os
import random
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import get_player, update_player

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

MOBS = {
    1: ["Zombie", "Wolf", "Slime", "Giant Spider"],
    2: ["Goblin Warrior", "Desert Bandit", "Cursed Skeleton", "Orc Raider"]
}

# Shop items catalog
SHOP_ITEMS = {
    "life potion": {"price": 25, "type": "heal", "desc": "Restore your life with /heal"},
    "basic armor": {"price": 200, "type": "armor", "desc": "[+2 def] An ugly armor made of wood"},
    "basic sword": {"price": 150, "type": "sword", "desc": "[+1 at] Better than nothing huh?"},
    "basic horse": {"price": 500, "type": "horse", "desc": "[tier I] Just a normie horse"},
    "dungeon key": {"price": 5000, "type": "item", "desc": "You need this key to enter the /dungeon"},
    "lottery ticket": {"price": 50, "type": "item", "desc": "To join the /lottery"},
    "seed": {"price": 4000, "type": "item", "desc": "Used to /farm"},
    "common lootbox": {"price": 800, "type": "lootbox", "desc": "It contains a few items, open with /open"},
    "uncommon lootbox": {"price": 6000, "type": "lootbox", "desc": "It contains some items, open with /open"},
    "rare lootbox": {"price": 40000, "type": "lootbox", "desc": "It contains many items, open with /open"},
    "epic lootbox": {"price": 150000, "type": "lootbox", "desc": "It contains a lot of items, open with /open"},
    "edgy lootbox": {"price": 420666, "type": "lootbox", "desc": "It contains a LOT of items, open with /open"},
    "life boost a": {"price": 10000, "type": "boost", "desc": "Provides +10 LIFE, temporary & not stackable"},
    "life boost b": {"price": 100000, "type": "boost", "desc": "Provides +25 LIFE, temporary & not stackable"},
    "life boost c": {"price": 1000000, "type": "boost", "desc": "Provides +50 LIFE, temporary & not stackable"},
    # Starlight Bundles
    "gatherer's pack": {"price": 400, "type": "bundle", "desc": "Contains 10x Starblossom Herbs & 5x Starlight Bulbs."},
    "miner's crate": {"price": 600, "type": "bundle", "desc": "Contains 10x Iron Ore & 3x Celestial Ore."},
    "hunter's cache": {"price": 750, "type": "bundle", "desc": "Contains 5x Goblin Fangs, 5x Slime Jellies & 2x Shadow Pelts."},
    "cosmic catalyst bundle": {"price": 1500, "type": "bundle", "desc": "Ultra Rare! Contains 1x Dragon Scale, 1x Serpentarius & +250 Stardust."}
}

class ShopPaginator(discord.ui.View):
    def __init__(self, user_name):
        super().__init__(timeout=60)
        self.user_name = user_name
        self.current_page = 1

    def create_embed(self):
        embed = discord.Embed(color=discord.Color.gold())
        if self.current_page == 1:
            embed.title = "Shop - Page 1/2"
            embed.description = f"**EPIC NPC:** Hey, {self.user_name}! Buy anything with `/buy [item]`\n"
            embed.add_field(name="Gear & Essentials", value=(
                "🧪 **life potion** | 25 🪙\n*Restore your life with /heal*\n"
                "📦 **basic armor** | 200 🪙\n*[+2 def] An ugly armor made of wood*\n"
                "🗡️ **basic sword** | 150 🪙\n*[+1 at] Better than nothing huh?*\n"
                "🐎 **basic horse** | 500 🪙\n*[tier I] Just a normie horse*\n"
                "🔑 **dungeon key** | 5,000 🪙\n*You need this key to enter the /dungeon*\n"
                "🎟️ **lottery ticket** | 50 🪙\n*To join the /lottery*\n"
                "🌱 **seed** | 4,000 🪙\n*Used to /farm*"
            ), inline=False)
        else:
            embed.title = "Shop - Page 2/2 & Starlight Bundles"
            embed.description = f"**EPIC NPC:** Hey, {self.user_name}! Buy anything with `/buy [item]`\n"
            embed.add_field(name="Lootboxes & Boosts", value=(
                "📦 **common lootbox** | 800 🪙\n📦 **uncommon lootbox** | 6,000 🪙\n"
                "📦 **rare lootbox** | 40,000 🪙\n📦 **epic lootbox** | 150,000 🪙\n"
                "📦 **edgy lootbox** | 420,666 🪙\n✨ **life boost a** | 10,000 🪙 (+10 LIFE)\n"
                "✨ **life boost b** | 100,000 🪙 (+25 LIFE)\n✨ **life boost c** | 1,000,000 🪙 (+50 LIFE)"
            ), inline=False)
            embed.add_field(name="✨ Starlight Bundles", value=(
                "📦 **Gatherer's Pack** | 400 ✨\n*Contains 10x Starblossom Herbs & 5x Starlight Bulbs.*\n"
                "📦 **Miner's Crate** | 600 ✨\n*Contains 10x Iron Ore & 3x Celestial Ore.*\n"
                "📦 **Hunter's Cache** | 750 ✨\n*Contains 5x Goblin Fangs, 5x Slime Jellies & 2x Shadow Pelts.*\n"
                "📦 **Cosmic Catalyst Bundle** | 1500 ✨\n*Ultra Rare! Contains 1x Dragon Scale, 1x Serpentarius & +250 Stardust.*"
            ), inline=False)
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 2
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("RvgRpg sandbox is online with full shop and bundles!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)

@bot.tree.command(name="profile", description="Check your RPG character stats and progress.")
async def profile(interaction: discord.Interaction):
    p = get_player(interaction.user.id)
    embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile", color=discord.Color.blurple())
    embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']} XP)\n**Area:** {p['area']}", inline=False)
    embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
    embed.add_field(name="MONEY", value=f"✨ **Wallet:** {p['wallet']}\n🏛️ **Bank:** {p['bank']}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="hunt", description="Hunt for monsters to gain XP and coins!")
async def hunt(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_player(uid)
    area = p.get("area", 1)
    mob_name = random.choice(MOBS.get(area, MOBS[1]))
    
    earned_coins = random.randint(15, 35) * area
    earned_xp = random.randint(10, 20) * area
    
    p["wallet"] += earned_coins
    p["xp"] += earned_xp
    
    level_up = ""
    if p["xp"] >= p["level"] * 100:
        p["level"] += 1
        p["xp"] = 0
        level_up = f"\n🎉 **LEVEL UP!** You reached Level {p['level']}!"

    update_player(uid, p)
    
    embed = discord.Embed(title=f"⚔️ Hunt Encounter", description=f"You fought and defeated a **{mob_name}** in Area {area}!", color=discord.Color.green())
    embed.add_field(name="REWARDS", value=f"✨ Coins: +{earned_coins}\n⭐ XP: +{earned_xp}{level_up}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="shop", description="Open the item shop with pages.")
async def shop(interaction: discord.Interaction):
    view = ShopPaginator(interaction.user.display_name)
    await interaction.response.send_message(embed=view.create_embed(), view=view)

@bot.tree.command(name="buy", description="Buy an item from the shop.")
async def buy(interaction: discord.Interaction, item: str):
    uid = str(interaction.user.id)
    p = get_player(uid)
    item_key = item.lower()
    
    if item_key not in SHOP_ITEMS:
        await interaction.response.send_message(f"❌ Item **'{item}'** not found in the shop!", ephemeral=True)
        return
        
    shop_item = SHOP_ITEMS[item_key]
    if p["wallet"] < shop_item["price"]:
        await interaction.response.send_message(f"❌ You don't have enough coins! This costs **{shop_item['price']} 🪙**.", ephemeral=True)
        return
        
    p["wallet"] -= shop_item["price"]
    p["inventory"][item_key] = p["inventory"].get(item_key, 0) + 1
    update_player(uid, p)
    
    await interaction.response.send_message(f"🛒 You successfully bought **1x {item}** for **{shop_item['price']} 🪙**!")

@bot.tree.command(name="deposit", description="Deposit coins into your bank.")
async def deposit(interaction: discord.Interaction, amount: int):
    uid = str(interaction.user.id)
    p = get_player(uid)
    if amount <= 0 or p['wallet'] < amount:
        await interaction.response.send_message("❌ Invalid amount or not enough coins in your wallet!", ephemeral=True)
        return
    p['wallet'] -= amount
    p['bank'] += amount
    update_player(uid, p)
    await interaction.response.send_message(f"🏛️ Successfully deposited **{amount} coins** into your bank.")

@bot.tree.command(name="daily", description="Claim your daily reward bonus.")
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_player(uid)
    bonus = 500
    p['wallet'] += bonus
    update_player(uid, p)
    await interaction.response.send_message(f"🎁 You claimed your daily reward of **{bonus} coins**!")

if __name__ == "__main__":
    bot.run(TOKEN)
