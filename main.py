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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("RvgRpg sandbox is online and fully loaded!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)

# --- PROFILE & STATS ---
@bot.tree.command(name="profile", description="Check your RPG character stats and progress.")
async def profile(interaction: discord.Interaction):
    p = get_player(interaction.user.id)
    embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile", color=discord.Color.blurple())
    embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']} XP)\n**Area:** {p['area']}", inline=False)
    embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
    embed.add_field(name="MONEY", value=f"✨ **Wallet:** {p['wallet']}\n🏛️ **Bank:** {p['bank']}", inline=False)
    await interaction.response.send_message(embed=embed)

# --- FIGHTING COMMANDS ---
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

@bot.tree.command(name="adventure", description="Go on an adventure for bigger rewards and risks!")
async def adventure(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_player(uid)
    coins = random.randint(50, 120) * p['area']
    p['wallet'] += coins
    update_player(uid, p)
    await interaction.response.send_message(f"🌲 You went on an epic adventure and brought back **{coins} coins**!")

@bot.tree.command(name="heal", description="Heal your HP back to maximum.")
async def heal(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_player(uid)
    p['hp'] = p['max_hp']
    update_player(uid, p)
    await interaction.response.send_message(f"❤️ You healed up! Your HP is fully restored to **{p['max_hp']}**.")

# --- ECONOMY COMMANDS ---
@bot.tree.command(name="shop", description="Open the item shop.")
async def shop(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Starlight RPG Shop", description="Available gear upgrades for Area 1:", color=discord.Color.gold())
    embed.add_field(name="Swords", value="• Wooden Sword - 500 coins\n• Stone Sword - 1500 coins", inline=False)
    embed.add_field(name="Armor", value="• Wooden Armor - 500 coins\n• Chainmail - 1500 coins", inline=False)
    await interaction.response.send_message(embed=embed)

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

# --- WORKING COMMANDS ---
@bot.tree.command(name="chop", description="Chop wood to gather materials.")
async def chop(interaction: discord.Interaction):
    await interaction.response.send_message("🪵 You swung your axe and chopped some wood!")

@bot.tree.command(name="fish", description="Fish in local waters for catches.")
async def fish(interaction: discord.Interaction):
    await interaction.response.send_message("🎣 You cast your line and caught a fish!")

# --- REWARDS COMMANDS ---
@bot.tree.command(name="daily", description="Claim your daily reward bonus.")
async def daily(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    p = get_player(uid)
    bonus = 200
    p['wallet'] += bonus
    update_player(uid, p)
    await interaction.response.send_message(f"🎁 You claimed your daily reward of **{bonus} coins**!")

if __name__ == "__main__":
    bot.run(TOKEN)
