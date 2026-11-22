import json
import os
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

os.makedirs(DATA_DIR, exist_ok=True)


def load_pets_data():
  if not os.path.exists(PETS_FILE):
    return {}
  try:
    with open(PETS_FILE, "r", encoding="utf-8") as f:
      return json.load(f)
  except json.JSONDecodeError:
    return {}


def save_pets_data(data):
  with open(PETS_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4)


HATCH_TIMES = {
    "Common Egg": 15 * 60,
    "Golden Egg": 2 * 60 * 60,
    "Celestial Egg": 6 * 60 * 60,
    "Void Egg": 4 * 60 * 60,
    "Transcendent Egg": 12 * 60 * 60,
}

EXPEDITION_TYPES = {
    "Short Patrol": {
        "duration": 30 * 60,
        "base_coins": 500,
        "material_chance": 0.3,
    },
    "Deep Forest Hunt": {
        "duration": 2 * 60 * 60,
        "base_coins": 3000,
        "material_chance": 0.6,
    },
    "Celestial Void Raid": {
        "duration": 6 * 60 * 60,
        "base_coins": 12000,
        "material_chance": 0.9,
    },
}

PET_DATABASE = {
    "Starlight Slime": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "+2% Coin bonus on commands",
        "buff_type": "coin",
        "value": 0.02,
    },
    "Pebble Crab": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "+1 Defense in quests",
        "buff_type": "defense",
        "value": 1,
    },
    "Shadow Mouse": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "-1% cooldown reduction",
        "buff_type": "cooldown",
        "value": 0.01,
    },
    "Sunwing Finch": {
        "rarity": "Uncommon",
        "type": "Golden Egg",
        "buff_desc": "+5% Expedition speed",
        "buff_type": "expedition",
        "value": 0.05,
    },
    "Crystal Hedgehog": {
        "rarity": "Uncommon",
        "type": "Golden Egg",
        "buff_desc": "+5% chance to find bonus crafting materials",
        "buff_type": "materials",
        "value": 0.05,
    },
    "Ember Fox": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "+10% Attack power during RPG battles",
        "buff_type": "attack",
        "value": 10,
    },
    "Glowtail Panther": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "+8% Coin bonus",
        "buff_type": "coin",
        "value": 0.08,
    },
    "Astral Phoenix": {
        "rarity": "Epic",
        "type": "Celestial Egg",
        "buff_desc": "5% chance to avoid failure on hard quests",
        "buff_type": "revive",
        "value": 0.05,
    },
    "Void Turtle": {
        "rarity": "Epic",
        "type": "Celestial Egg",
        "buff_desc": "+15% defense and massive material yield on expeditions",
        "buff_type": "defense_material",
        "value": 0.15,
    },
    "Nebula Dragon": {
        "rarity": "Legendary",
        "type": "Celestial Egg",
        "buff_desc": "+25% total coin multiplier & +15 attack power",
        "buff_type": "coin_attack",
        "value": (0.25, 15),
    },
    "Starlight Celestial Spirit": {
        "rarity": "Legendary",
        "type": "Celestial Egg",
        "buff_desc": "-10% cooldown reduction (+Coin gain & double rare drops)",
        "buff_type": "cooldown_ultimate",
        "value": 0.10,
    },
    "Mossy Badger": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "-3% cooldown reduction, +5% gathering yield",
        "buff_type": "cooldown_gathering",
        "value": (0.03, 0.05),
    },
    "Tidepool Crab": {
        "rarity": "Uncommon",
        "type": "Common Egg",
        "buff_desc": "-4% cooldown reduction, +8% fish/pearl drop chance",
        "buff_type": "cooldown_fishing",
        "value": (0.04, 0.08),
    },
    "Sunbeam Fox": {
        "rarity": "Uncommon",
        "type": "Golden Egg",
        "buff_desc": "-6% cooldown reduction, +5% coin payout",
        "buff_type": "cooldown_coin",
        "value": (0.06, 0.05),
    },
    "Glimmer Owl": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "-7% cooldown reduction, +5% XP gain",
        "buff_type": "cooldown_xp",
        "value": (0.07, 0.05),
    },
    "Cinder Lynx": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "-9% cooldown reduction, +3% crit chance",
        "buff_type": "cooldown_crit",
        "value": (0.09, 0.03),
    },
    "Tempest Drake": {
        "rarity": "Epic",
        "type": "Celestial Egg",
        "buff_desc": "-12% cooldown reduction, +8% coins & +5% XP",
        "buff_type": "cooldown_coin_xp",
        "value": (0.12, 0.08, 0.05),
    },
    "Aether Phoenix": {
        "rarity": "Mythic",
        "type": "Celestial Egg",
        "buff_desc": "-14% cooldown reduction, +5% crit & HP recovery boost",
        "buff_type": "cooldown_crit_heal",
        "value": (0.14, 0.05, 0.05),
    },
    "Singularity Kitsune": {
        "rarity": "Void",
        "type": "Celestial Egg",
        "buff_desc": "-15% cooldown reduction, +6% crit & +10% rare drop chance",
        "buff_type": "cooldown_crit_rare",
        "value": (0.15, 0.06, 0.10),
    },
    "Abyssal Stalker": {
        "rarity": "Abyssal",
        "type": "Void Egg",
        "buff_desc": "-11% cooldown reduction, +12% rare drop chance & +10% expedition coins",
        "buff_type": "cooldown_abyssal",
        "value": (0.11, 0.12, 0.10),
    },
    "Prime Seraph": {
        "rarity": "Transcendent",
        "type": "Transcendent Egg",
        "buff_desc": "-15% cooldown reduction, +20% coin payout, +10% XP & +10% crit chance",
        "buff_type": "cooldown_transcendent",
        "value": (0.15, 0.20, 0.10, 0.10),
    },
}


class PetsCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(
      name="hatch",
      description=(
          "Place an egg from your inventory into your incubator to start"
          " hatching!"
      ),
  )
  @app_commands.choices(egg_type=[
      app_commands.Choice(name="Common Egg (15m)", value="Common Egg"),
      app_commands.Choice(name="Golden Egg (2h)", value="Golden Egg"),
      app_commands.Choice(name="Celestial Egg (6h)", value="Celestial Egg"),
      app_commands.Choice(name="Void Egg (4h)", value="Void Egg"),
      app_commands.Choice(
          name="Transcendent Egg (12h)", value="Transcendent Egg"
      ),
  ])
  async def hatch(self, interaction: discord.Interaction, egg_type: str):
    user_id = str(interaction.user.id)
    data = load_pets_data()
    user_data = data.setdefault(
        user_id,
        {
            "inventory": [],
            "active_pet": None,
            "incubating": None,
            "expedition": None,
        },
    )

    if user_data.get("incubating"):
      await interaction.response.send_message(
          "❌ Your incubator is already busy! Use `/incubator` to check status"
          " or `/claim` when it's finished.",
          ephemeral=True,
      )
      return

    player = get_player(user_id)
    inv = player.setdefault("inventory", {})
    egg_key = egg_type.lower()
    owned_eggs = inv.get(egg_key, 0)

    if owned_eggs < 1:
      await interaction.response.send_message(
          f"❌ You don't have a **{egg_type}** in your inventory! Check `/shop`"
          " or claim one from a bundle.",
          ephemeral=True,
      )
      return

    inv[egg_key] = owned_eggs - 1
    if inv[egg_key] <= 0:
      inv.pop(egg_key, None)
    update_player(user_id, player)

    duration = HATCH_TIMES[egg_type]
    finish_time = time.time() + duration

    user_data["incubating"] = {"egg_type": egg_type, "finish_time": finish_time}
    save_pets_data(data)

    embed = discord.Embed(
        title="🥚 Incubator Started!",
        description=(
            f"You placed a **{egg_type}** into the incubator.\nCheck back in"
            " using `/incubator` to monitor its progress!"
        ),
        color=discord.Color.orange(),
    )
    embed.set_footer(text=f"Hatch Time: {egg_type}")
    await interaction.response.send_message(embed=embed)

  @app_commands.command(
      name="incubator",
      description="Check the status of your currently incubating egg.",
  )
  async def incubator(self, interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_pets_data()

    user_data = data.get(user_id, {})
    incubating = user_data.get("incubating")

    embed = discord.Embed(
        title="⚙️ Starlight Incubator", color=discord.Color.blurple()
    )

    if not incubating:
      embed.description = (
          "Your incubator is currently empty. Use `/hatch` to start incubating"
          " an egg!"
      )
    else:
      egg_type = incubating["egg_type"]
      finish_time = incubating["finish_time"]
      remaining = int(finish_time - time.time())

      if remaining <= 0:
        embed.description = (
            f"🎉 Your **{egg_type}** has finished hatching! Run **`/claim`**"
            " to see what you got!"
        )
        embed.color = discord.Color.green()
      else:
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        time_str = (
            f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
        )
        embed.description = (
            f"Incubating: **{egg_type}**\n⏱️ **Time Remaining:** {time_str}"
        )
        embed.color = discord.Color.gold()

    await interaction.response.send_message(embed=embed)

  @app_commands.command(
      name="claim", description="Claim your hatched pet from the incubator."
  )
  async def claim(self, interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_pets_data()

    user_data = data.setdefault(
        user_id,
        {
            "inventory": [],
            "active_pet": None,
            "incubating": None,
            "expedition": None,
        },
    )
    incubating = user_data.get("incubating")

    if not incubating:
      await interaction.response.send_message(
          "❌ You don't have anything currently incubating in your incubator!",
          ephemeral=True,
      )
      return

    remaining = int(incubating["finish_time"] - time.time())
    if remaining > 0:
      mins, secs = divmod(remaining, 60)
      hours, mins = divmod(mins, 60)
      time_str
