import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

class StarlightBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("rpg_cog")
        await self.load_extension("party_cog")
        await self.load_extension("quests_cog")
        await self.load_extension("tickets_cog")
        await self.load_extension("embed_cog")
        await self.load_extension("pets_cog")
        await self.load_extension("inventory_cog")
        await self.load_extension("marketplace_cog")
        await self.load_extension("guilds_cog")
        await self.load_extension("dungeons_cog")  # Added 100-Floor Starlight Spire Cog!
        await self.load_extension("area_expansions_cog")  # Added Area-Locked Expansion Commands!
        
        TEST_GUILD_ID = 1570758404476244120
        guild = discord.Object(id=TEST_GUILD_ID)

        try:
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Successfully synced {len(synced)} commands instantly to your server!")
        except Exception as e:
            print(f"Failed to sync tree: {e}")

bot = StarlightBot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Starlight RPG engine is fully online!")

bot.run(TOKEN)
