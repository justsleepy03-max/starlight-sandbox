import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import get_player

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("RvgRpg sandbox is online!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print(e)

@bot.tree.command(name="profile", description="Check your RPG character stats and progress.")
async def profile(interaction: discord.Interaction):
    p = get_player(interaction.user.id)

    embed = discord.Embed(
        title=f"✨ {interaction.user.display_name}'s Profile",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="PROGRESS",
        value=f"**Level:** {p['level']} ({p['xp']} XP)\n**Area:** {p['area']}",
        inline=False
    )
    embed.add_field(
        name="STATS",
        value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}",
        inline=False
    )
    embed.add_field(
        name="MONEY",
        value=f"✨ **Wallet:** {p['wallet']}\n🏛️ **Bank:** {p['bank']}",
        inline=False
    )

    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(TOKEN)
