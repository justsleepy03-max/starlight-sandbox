import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True


class StarlightBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self._has_printed_ready = False

    async def setup_hook(self):
        extensions = [
            "rpg_cog",
            "shop_cog",
            "crafting_cog",
            "party_cog",
            "quests_cog",
            "tickets_cog",
            "embed_cog",
            "pets_cog",
            "inventory_cog",
            "marketplace_cog",
            "guilds_cog",
            "dungeons_cog",          # Added 100-Floor Starlight Spire Cog!
            "area_expansions_cog",   # Added Area-Locked Expansion Commands!
            "utility_cog",           # Added /utility sub-menu & /equip commands!
            "stats_leaderboard_cog", # Added /stats & /leaderboard cog!
        ]

        for ext in extensions:
            await self.load_extension(ext)

        test_guild_id = 1570758404476244120
        guild = discord.Object(id=test_guild_id)

        try:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Successfully synced {len(synced)} commands instantly to your server!")
        except Exception as e:
            print(f"Failed to sync tree: {e}")


bot = StarlightBot()


@bot.event
async def on_ready():
    if not bot._has_printed_ready:
        bot._has_printed_ready = True
        print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
        print("Starlight RPG engine is fully online!")


bot.run(TOKEN)
