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
        "gear_cog",  # Added /gear equipment & tier restriction cog!
        "party_cog",
        "quests_cog",
        "tickets_cog",
        "embed_cog",
        "pets_cog",
        "inventory_cog",
        "marketplace_cog",
        "guilds_cog",
        "dungeons_cog",  # Added 100-Floor Starlight Spire Cog!
        "area_expansions_cog",  # Added Area-Locked Expansion Commands!
        "cooking_quests_cog",  # Added interactive /kitchen recipes, buffs & daily commissions cog!
        "utility_cog",  # Added /utility sub-menu & /equip commands!
        "stats_leaderboard_cog",  # Added /stats & /leaderboard cog!
        "feedback_cog",  # Added /feedback beta reporting cog!
        "help_cog",  # Added interactive /help button menu cog!
        "custom_bundle_cog",  # Added owner-only /custombundle, /setcustombundle & /listcustombundles cog!
        "release_scheduler_cog",  # Scheduled releases cog (Dec 4, 2026 @ 10:00 AM GMT)
        "admin_cog",  # Added owner-only /wipe command with confirmation & backup!
    ]

    for ext in extensions:
      if ext not in self.extensions:
        await self.load_extension(ext)

    test_guild_id = 1570758404476244120
    rvg_guild_id = None  # Optional: Replace None with RVG's Server ID (digits only) for instant sync

    try:
      # 1. Sync globally so RVG and all future servers get commands automatically
      global_synced = await self.tree.sync()
      print(f"Successfully synced {len(global_synced)} global commands!")

      # 2. Instant guild sync for your test server (and RVG if ID is set)
      guild_ids = [test_guild_id]
      if rvg_guild_id:
        guild_ids.append(rvg_guild_id)

      for gid in guild_ids:
        guild = discord.Object(id=gid)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        print(f"Instantly synced {len(synced)} commands to server {gid}!")
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
