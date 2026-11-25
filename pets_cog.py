from datetime import datetime, timezone
import json
import os
import random
import shutil
import threading
import time
import uuid
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")
TEMP_PETS_FILE = os.path.join(DATA_DIR, "pets.json.tmp")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

PART_1_RELEASE_UTC = datetime(2026, 12, 4, 10, 0, tzinfo=timezone.utc)
PART_1_PET_NAMES = {
    "Cinderkit",
    "Glacifin",
    "Mossling",
    "Voltlynx",
    "Duskweaver",
    "Aegisdrake",
}

MAX_EQUIPPED_MOVES = 4
MOVE_UNLOCK_INTERVAL = 5

_PETS_LOCK = threading.Lock()
os.makedirs(DATA_DIR, exist_ok=True)


def part1_unlocked() -> bool:
  return datetime.now(timezone.utc) >= PART_1_RELEASE_UTC


def backup_pets_data(label="manual"):
  with _PETS_LOCK:
    if not os.path.exists(PETS_FILE):
      return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"pets_{label}_{stamp}.json")
    shutil.copy2(PETS_FILE, dest)
    return dest


def load_pets_data():
  with _PETS_LOCK:
    if not os.path.exists(PETS_FILE):
      return {}
    try:
      with open(PETS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
      os.makedirs(BACKUP_DIR, exist_ok=True)
      stamp = time.strftime("%Y%m%d-%H%M%S")
      corrupt_copy = os.path.join(BACKUP_DIR, f"pets_corrupt_{stamp}.json")
      try:
        shutil.copy2(PETS_FILE, corrupt_copy)
      except OSError:
        pass
      raise RuntimeError(
          f"Failed to load {PETS_FILE}; backup saved to {corrupt_copy}"
      ) from exc


def save_pets_data(data):
  with _PETS_LOCK:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TEMP_PETS_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, indent=4)
    os.replace(TEMP_PETS_FILE, PETS_FILE)


# Incubation durations in seconds
HATCH_TIMES = {
    "Common Egg": 15 * 60,  # 15 minutes
    "Golden Egg": 2 * 60 * 60,  # 2 hours
    "Celestial Egg": 6 * 60 * 60,  # 6 hours
}

# Pre-Part-1 Expedition Durations and Rewards (active before Dec 4, 10:00 UTC)
LEGACY_EXPEDITION_TYPES = {
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

# Part 1 Balanced 10-30 Minute Expeditions (active from Dec 4, 10:00 UTC)
PART_1_EXPEDITION_TYPES = {
    "Quick Scout": {
        "duration": 10 * 60,  # 10 minutes
        "pet_xp": 25,
        "coin_pool": [
            {"amount": 150, "weight": 50},
            {"amount": 250, "weight": 35},
            {"amount": 450, "weight": 15},
        ],
        "loot_pool": [
            {"item": None, "qty": 0, "weight": 45},
            {"item": "starlight_dust", "qty": 1, "weight": 35},
            {"item": "beast_fang", "qty": 1, "weight": 15},
            {"item": "astral_shard", "qty": 1, "weight": 5},
        ],
    },
    "Timberline Trek": {
        "duration": 20 * 60,  # 20 minutes
        "pet_xp": 55,
        "coin_pool": [
            {"amount": 350, "weight": 45},
            {"amount": 600, "weight": 35},
            {"amount": 1000, "weight": 20},
        ],
        "loot_pool": [
            {"item": None, "qty": 0, "weight": 30},
            {"item": "starlight_dust", "qty": 2, "weight": 35},
            {"item": "beast_fang", "qty": 2, "weight": 25},
            {"item": "astral_shard", "qty": 1, "weight": 10},
        ],
    },
    "Starfall Delve": {
        "duration": 30 * 60,  # 30 minutes
        "pet_xp": 95,
        "coin_pool": [
            {"amount": 700, "weight": 40},
            {"amount": 1200, "weight": 40},
            {"amount": 2000, "weight": 20},
        ],
        "loot_pool": [
            {"item": None, "qty": 0, "weight": 20},
            {"item": "starlight_dust", "qty": 3, "weight": 30},
            {"item": "beast_fang", "qty": 3, "weight": 30},
            {"item": "astral_shard", "qty": 2, "weight": 20},
        ],
    },
}


def get_active_expedition_types(unlocked: bool | None = None) -> dict:
  if unlocked is None:
    unlocked = part1_unlocked()
  return PART_1_EXPEDITION_TYPES if unlocked else LEGACY_EXPEDITION_TYPES


DEFAULT_MOVE_POOL = [
    "Quick Strike",
    "Guard Pulse",
    "Focus Surge",
    "Starlight Burst",
    "Apex Roar",
]

# Pet Roster Definitions (Existing + Part 1 Lineup)
PET_DATABASE = {
    "Starlight Slime": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "+2% Coin bonus on commands",
        "buff_type": "coin",
        "value": 0.02,
        "moves": [
            "Gelatin Bounce",
            "Sparkle Splash",
            "Sticky Guard",
            "Starlight Pop",
            "Nova Blob",
        ],
    },
    "Pebble Crab": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "+1 Defense in quests",
        "buff_type": "defense",
        "value": 1,
        "moves": [
            "Shell Snap",
            "Gravel Toss",
            "Carapace Brace",
            "Tide Pinch",
            "Crag Slam",
        ],
    },
    "Shadow Mouse": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "-1% cooldown reduction",
        "buff_type": "cooldown",
        "value": 0.01,
        "moves": [
            "Nimble Nib",
            "Dusk Dash",
            "Sneak Feint",
            "Gloom Scurry",
            "Phantom Whisker",
        ],
    },
    "Sunwing Finch": {
        "rarity": "Uncommon",
        "type": "Golden Egg",
        "buff_desc": "+5% Expedition speed",
        "buff_type": "expedition",
        "value": 0.05,
        "moves": [
            "Dawn Peck",
            "Wing Gust",
            "Solar Chirp",
            "Sky Dive",
            "Sunburst Talon",
        ],
    },
    "Crystal Hedgehog": {
        "rarity": "Uncommon",
        "type": "Golden Egg",
        "buff_desc": "+5% chance to find bonus crafting materials",
        "buff_type": "materials",
        "value": 0.05,
        "moves": [
            "Quill Shot",
            "Prism Roll",
            "Facet Shield",
            "Gem Spike",
            "Crystalline Barrage",
        ],
    },
    "Ember Fox": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "+10% Attack power during RPG battles",
        "buff_type": "attack",
        "value": 10,
        "moves": [
            "Ember Fang",
            "Cinder Pounce",
            "Heatwave Tail",
            "Blaze Claw",
            "Inferno Rush",
        ],
    },
    "Glowtail Panther": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "+8% Coin bonus",
        "buff_type": "coin",
        "value": 0.08,
        "moves": [
            "Neon Stalk",
            "Lumen Slash",
            "Night Prowl",
            "Prism Leap",
            "Starlight Pounce",
        ],
    },
    "Astral Phoenix": {
        "rarity": "Epic",
        "type": "Celestial Egg",
        "buff_desc": "5% chance to avoid failure on hard quests",
        "buff_type": "revive",
        "value": 0.05,
        "moves": [
            "Solar Flare",
            "Ash Renewal",
            "Celestial Wing",
            "Pyre Dive",
            "Rebirth Nova",
        ],
    },
    "Void Turtle": {
        "rarity": "Epic",
        "type": "Celestial Egg",
        "buff_desc": (
            "+15% defense and massive material yield on expeditions"
        ),
        "buff_type": "defense_material",
        "value": 0.15,
        "moves": [
            "Void Shell",
            "Abyssal Pulse",
            "Rift Anchor",
            "Gravity Stomp",
            "Eventide Bastion",
        ],
    },
    "Nebula Dragon": {
        "rarity": "Legendary",
        "type": "Celestial Egg",
        "buff_desc": "+25% total coin multiplier & +15 attack power",
        "buff_type": "coin_attack",
        "value": (0.25, 15),
        "moves": [
            "Cosmic Breath",
            "Stardust Rend",
            "Orbit Strike",
            "Galaxy Roar",
            "Supernova Bite",
        ],
    },
    "Starlight Celestial Spirit": {
        "rarity": "Legendary",
        "type": "Celestial Egg",
        "buff_desc": "-10% cooldown reduction (+Coin gain & double rare drops)",
        "buff_type": "cooldown_ultimate",
        "value": 0.10,
        "moves": [
            "Astral Hymn",
            "Chrono Thread",
            "Celestial Veil",
            "Starfall Lance",
            "Eternal Dawn",
        ],
    },
    # Part 1 Expansion Pets (gated until Dec 4, 2026 10:00 UTC)
    "Cinderkit": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "Boosts quest rewards and ember strike power",
        "buff_type": "quest_ember",
        "value": 0.05,
        "moves": [
            "Ember Scratch",
            "Cinder Spark",
            "Warm Purr",
            "Flare Pounce",
            "Blaze Whisker",
        ],
    },
    "Glacifin": {
        "rarity": "Common",
        "type": "Common Egg",
        "buff_desc": "Boosts expedition haul consistency and frost guard",
        "buff_type": "expedition_frost",
        "value": 0.05,
        "moves": [
            "Frost Fin",
            "Chill Spray",
            "Ice Ward",
            "Glacier Tail",
            "Rime Surge",
        ],
    },
    "Mossling": {
        "rarity": "Uncommon",
        "type": "Golden Egg",
        "buff_desc": "Boosts gathering/quest yield and natural recovery",
        "buff_type": "quest_moss",
        "value": 0.07,
        "moves": [
            "Vine Whip",
            "Spore Puff",
            "Bark Shield",
            "Root Snare",
            "Overgrowth Slam",
        ],
    },
    "Voltlynx": {
        "rarity": "Rare",
        "type": "Golden Egg",
        "buff_desc": "Boosts expedition speed and spark strike speed",
        "buff_type": "expedition_volt",
        "value": 0.08,
        "moves": [
            "Static Claw",
            "Arc Dash",
            "Charged Coat",
            "Thunder Leap",
            "Storm Fang",
        ],
    },
    "Duskweaver": {
        "rarity": "Epic",
        "type": "Celestial Egg",
        "buff_desc": "Boosts quest loot chances and twilight hexes",
        "buff_type": "quest_dusk",
        "value": 0.10,
        "moves": [
            "Shadow Thread",
            "Gloom Veil",
            "Umbral Ward",
            "Eclipse Bind",
            "Astral Loom",
        ],
    },
    "Aegisdrake": {
        "rarity": "Legendary",
        "type": "Celestial Egg",
        "buff_desc": "Boosts expedition rewards, quest guard, and draconic might",
        "buff_type": "expedition_aegis",
        "value": 0.15,
        "moves": [
            "Scale Bash",
            "Aegis Roar",
            "Wyrm Guard",
            "Starflame Breath",
            "Sovereign Dive",
        ],
    },
}


def _weighted_choice(entries: list[dict], key: str):
  weights = [max(0, e.get("weight", 0)) for e in entries]
  if not entries or sum(weights) <= 0:
    return entries[0][key] if entries else None
  chosen = random.choices(entries, weights=weights, k=1)[0]
  return chosen[key]


def _xp_needed_for_level(level: int) -> int:
  return 50 + (max(1, level) - 1) * 35


def _compute_unlocked_moves(
    pet_name: str, level: int, moves_feature_unlocked: bool
) -> list[str]:
  if not moves_feature_unlocked:
    return []
  pool = PET_DATABASE.get(pet_name, {}).get("moves") or DEFAULT_MOVE_POOL
  unlock_count = (
      max(1, max(1, level) // MOVE_UNLOCK_INTERVAL)
      if level >= MOVE_UNLOCK_INTERVAL
      else 0
  )
  return pool[: min(len(pool), unlock_count)]


def _create_pet_record(
    pet_name: str, moves_feature_unlocked: bool | None = None
) -> dict:
  pet_info = PET_DATABASE[pet_name]
  if moves_feature_unlocked is None:
    moves_feature_unlocked = part1_unlocked()
  unlocked_moves = _compute_unlocked_moves(pet_name, 1, moves_feature_unlocked)
  return {
      "pet_id": f"pet_{uuid.uuid4().hex[:8]}",
      "name": pet_name,
      "rarity": pet_info["rarity"],
      "buff": pet_info["buff_desc"],
      "level": 1,
      "xp": 0,
      "unlocked_moves": unlocked_moves,
      "equipped_moves": unlocked_moves[:MAX_EQUIPPED_MOVES],
  }


def _normalize_pet_entry(
    pet: dict, moves_feature_unlocked: bool | None = None
) -> dict:
  if not isinstance(pet, dict):
    return _create_pet_record(
        "Starlight Slime", moves_feature_unlocked=moves_feature_unlocked
    )
  if moves_feature_unlocked is None:
    moves_feature_unlocked = part1_unlocked()

  name = pet.get("name", "Starlight Slime")
  info = PET_DATABASE.get(name, {})
  level = max(1, int(pet.get("level", 1) or 1))
  xp = max(0, int(pet.get("xp", 0) or 0))
  pet["pet_id"] = pet.get("pet_id") or f"pet_{uuid.uuid4().hex[:8]}"
  pet["name"] = name
  pet["rarity"] = pet.get("rarity") or info.get("rarity", "Common")
  pet["buff"] = pet.get("buff") or info.get("buff_desc", "No passive buff")
  pet["level"] = level
  pet["xp"] = xp

  if not moves_feature_unlocked:
    pet["unlocked_moves"] = []
    pet["equipped_moves"] = []
    return pet

  expected_moves = _compute_unlocked_moves(name, level, True)
  existing_unlocked = pet.get("unlocked_moves")
  if isinstance(existing_unlocked, list) and existing_unlocked:
    merged_unlocked = list(dict.fromkeys(existing_unlocked + expected_moves))
  else:
    merged_unlocked = expected_moves
  pet["unlocked_moves"] = merged_unlocked

  equipped = pet.get("equipped_moves")
  if isinstance(equipped, list) and equipped:
    pet["equipped_moves"] = [
        m for m in equipped if m in merged_unlocked
    ][:MAX_EQUIPPED_MOVES]
  else:
    pet["equipped_moves"] = merged_unlocked[:MAX_EQUIPPED_MOVES]
  return pet


def _apply_pet_xp(pet: dict, gained_xp: int) -> dict:
  moves_feature_unlocked = part1_unlocked()
  pet = _normalize_pet_entry(pet, moves_feature_unlocked=moves_feature_unlocked)
  pet["xp"] += max(0, int(gained_xp))
  leveled_up = False
  newly_unlocked = []

  while pet["xp"] >= _xp_needed_for_level(pet["level"]):
    pet["xp"] -= _xp_needed_for_level(pet["level"])
    pet["level"] += 1
    leveled_up = True

    if moves_feature_unlocked:
      before_moves = set(pet["unlocked_moves"])
      updated_moves = _compute_unlocked_moves(pet["name"], pet["level"], True)
      for move in updated_moves:
        if move not in pet["unlocked_moves"]:
          pet["unlocked_moves"].append(move)
          newly_unlocked.append(move)
        if (
            move not in before_moves
            and len(pet["equipped_moves"]) < MAX_EQUIPPED_MOVES
        ):
          pet["equipped_moves"].append(move)

  return {
      "leveled_up": leveled_up,
      "new_level": pet["level"],
      "newly_unlocked": newly_unlocked,
  }


def _normalize_user_data(data: dict, user_id: str) -> dict:
  moves_feature_unlocked = part1_unlocked()
  user_data = data.setdefault(
      user_id,
      {
          "inventory": [],
          "active_pet": None,
          "incubating": None,
          "expedition": None,
      },
  )
  user_data.setdefault("inventory", [])
  user_data.setdefault("active_pet", None)
  user_data.setdefault("incubating", None)
  user_data.setdefault("expedition", None)

  normalized_inv = [
      _normalize_pet_entry(p, moves_feature_unlocked=moves_feature_unlocked)
      for p in user_data["inventory"]
  ]
  user_data["inventory"] = normalized_inv

  active_pet = user_data.get("active_pet")
  if isinstance(active_pet, dict):
    active_pet = _normalize_pet_entry(
        active_pet, moves_feature_unlocked=moves_feature_unlocked
    )
    matched = next(
        (p for p in normalized_inv if p["pet_id"] == active_pet["pet_id"]),
        None,
    )
    if matched is None:
      matched = next(
          (p for p in normalized_inv if p["name"] == active_pet["name"]),
          None,
      )
    if matched is not None:
      user_data["active_pet"] = matched
    else:
      user_data["active_pet"] = active_pet

  return user_data


def _pick_from_pool(candidates: list[str], unlocked: bool) -> str:
  if not unlocked:
    filtered = [name for name in candidates if name not in PART_1_PET_NAMES]
    if filtered:
      candidates = filtered
  return random.choice(candidates)


def _roll_hatched_pet(egg_type: str, unlocked: bool) -> str:
  roll = random.random()

  if egg_type == "Common Egg":
    if roll < 0.70:
      pool = ["Starlight Slime", "Pebble Crab", "Shadow Mouse", "Cinderkit", "Glacifin"]
    elif roll < 0.92:
      pool = ["Sunwing Finch", "Crystal Hedgehog"]
    else:
      pool = ["Ember Fox", "Glowtail Panther"]

  elif egg_type == "Golden Egg":
    if roll < 0.55:
      pool = ["Sunwing Finch", "Crystal Hedgehog", "Mossling"]
    elif roll < 0.88:
      pool = ["Ember Fox", "Glowtail Panther", "Voltlynx"]
    else:
      pool = ["Astral Phoenix", "Void Turtle"]

  elif egg_type == "Celestial Egg":
    if roll < 0.70:
      pool = ["Astral Phoenix", "Void Turtle", "Duskweaver"]
    else:
      pool = ["Nebula Dragon", "Starlight Celestial Spirit", "Aegisdrake"]
  else:
    pool = ["Starlight Slime", "Pebble Crab", "Shadow Mouse", "Cinderkit", "Glacifin"]

  return _pick_from_pool(pool, unlocked)


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
  @app_commands.choices(
      egg_type=[
          app_commands.Choice(name="Common Egg (15m)", value="Common Egg"),
          app_commands.Choice(name="Golden Egg (2h)", value="Golden Egg"),
          app_commands.Choice(
              name="Celestial Egg (6h)", value="Celestial Egg"
          ),
      ]
  )
  async def hatch(self, interaction: discord.Interaction, egg_type: str):
    user_id = str(interaction.user.id)
    data = load_pets_data()
    user_data = _normalize_user_data(data, user_id)

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
            f"🎉 Your **{egg_type}** has finished hatching! Run **`/claim`** to"
            " see what you got!"
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
    user_data = _normalize_user_data(data, user_id)
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
      time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
      await interaction.response.send_message(
          f"⏳ Your egg is still hatching! Come back in **{time_str}** or"
          " check `/incubator`.",
          ephemeral=True,
      )
      return

    egg_type = incubating["egg_type"]
    unlocked = part1_unlocked()
    hatched_pet_name = _roll_hatched_pet(egg_type, unlocked)
    new_pet = _create_pet_record(
        hatched_pet_name, moves_feature_unlocked=unlocked
    )

    user_data["incubating"] = None
    user_data["inventory"].append(new_pet)
    save_pets_data(data)

    moves_line = (
        f"\n**Moves:** {', '.join(new_pet['equipped_moves'])}"
        if unlocked and new_pet.get("equipped_moves")
        else ""
    )

    embed = discord.Embed(
        title="✨ Egg Claimed Successfully!",
        description=f"Your **{egg_type}** hatched into...",
        color=discord.Color.gold(),
    )
    embed.add_field(
        name=f"🐾 {new_pet['name']} ({new_pet['rarity']}) • Lv.{new_pet['level']}",
        value=f"**Buff:** {new_pet['buff']}{moves_line}",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)

  @app_commands.command(
      name="pets", description="View your pet collection and active companion."
  )
  async def pets(self, interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_pets_data()
    user_data = _normalize_user_data(data, user_id)

    inventory = user_data.get("inventory", [])
    active_pet = user_data.get("active_pet")
    moves_unlocked = part1_unlocked()

    embed = discord.Embed(
        title=f"🐾 {interaction.user.display_name}'s Pet Collection",
        color=discord.Color.blurple(),
    )

    if active_pet:
      needed = _xp_needed_for_level(active_pet["level"])
      moves_line = ""
      if moves_unlocked:
        moves_str = ", ".join(active_pet.get("equipped_moves", [])) or "None"
        moves_line = f"\n*Moves:* {moves_str}"
      embed.add_field(
          name="🟢 Active Companion",
          value=(
              f"**{active_pet['name']}** ({active_pet['rarity']}) • "
              f"**Lv.{active_pet['level']}** ({active_pet['xp']}/{needed} XP)\n"
              f"*Buff:* {active_pet['buff']}{moves_line}"
          ),
          inline=False,
      )
    else:
      embed.add_field(
          name="🟢 Active Companion",
          value="None equipped. Use `/equip` to choose one!",
          inline=False,
      )

    if not inventory:
      embed.description = (
          "Your inventory is empty! Incubate and hatch some eggs to start your"
          " collection."
      )
    else:
      pet_lines = []
      for p in inventory:
        needed = _xp_needed_for_level(p["level"])
        pet_lines.append(
            f"• **{p['name']}** ({p['rarity']}) • **Lv.{p['level']}** "
            f"[{p['xp']}/{needed} XP] — *{p['buff']}*"
        )
      embed.add_field(
          name=f"📦 All Pets ({len(inventory)})",
          value="\n".join(pet_lines),
          inline=False,
      )

    await interaction.response.send_message(embed=embed)

  @app_commands.command(
      name="equip",
      description="Equip a companion from your inventory to gain its passive buff.",
  )
  async def equip(self, interaction: discord.Interaction, pet_name: str):
    user_id = str(interaction.user.id)
    data = load_pets_data()
    user_data = _normalize_user_data(data, user_id)

    inventory = user_data.get("inventory", [])
    matching_pet = next(
        (p for p in inventory if p["name"].lower() == pet_name.lower()), None
    )

    if not matching_pet:
      await interaction.response.send_message(
          f"❌ You don't own a pet named **{pet_name}** in your inventory.",
          ephemeral=True,
      )
      return

    user_data["active_pet"] = matching_pet
    save_pets_data(data)

    await interaction.response.send_message(
        f"✅ Successfully equipped **{matching_pet['name']}** "
        f"(Lv.{matching_pet['level']})! Its passive buff is now active."
    )

  @app_commands.command(
      name="expedition",
      description=(
          "Send your active pet out on a timed adventure for coins and loot!"
      ),
  )
  async def expedition(
      self, interaction: discord.Interaction, expedition_type: str
  ):
    user_id = str(interaction.user.id)
    data = load_pets_data()
    user_data = _normalize_user_data(data, user_id)
    unlocked = part1_unlocked()
    exp_table = get_active_expedition_types(unlocked)

    if expedition_type not in exp_table:
      valid_list = ", ".join(f"`{k}`" for k in exp_table.keys())
      await interaction.response.send_message(
          f"❌ Unknown expedition type `{expedition_type}`. Available right now:"
          f" {valid_list}",
          ephemeral=True,
      )
      return

    active_pet = user_data.get("active_pet")
    if not active_pet:
      await interaction.response.send_message(
          "❌ You must have an active pet equipped (`/equip`) before sending"
          " them on an expedition!",
          ephemeral=True,
      )
      return

    if user_data.get("expedition"):
      await interaction.response.send_message(
          "❌ Your pet is already out on an expedition! Check status with"
          " `/expedition-status` or claim when ready.",
          ephemeral=True,
      )
      return

    base_duration = exp_table[expedition_type]["duration"]

    # Apply expedition speed passive buff (-5% duration)
    if active_pet.get("name") == "Sunwing Finch":
      base_duration = int(base_duration * 0.95)

    finish_time = time.time() + base_duration
    user_data["expedition"] = {
        "type": expedition_type,
        "finish_time": finish_time,
        "pet_id": active_pet.get("pet_id"),
        "pet_name": active_pet["name"],
    }
    save_pets_data(data)

    mins = max(1, base_duration // 60)
    embed = discord.Embed(
        title="🗺️ Pet Expedition Started!",
        description=(
            f"**{active_pet['name']}** set off on a **{expedition_type}**"
            f" (~{mins}m)!"
        ),
        color=discord.Color.green(),
    )
    embed.add_field(
        name="Companion Buff Active", value=active_pet["buff"], inline=False
    )
    embed.set_footer(
        text="Check back when the timer completes to claim your rewards!"
    )
    await interaction.response.send_message(embed=embed)

  @app_commands.command(
      name="expedition-status",
      description="Check the progress of your pet's current expedition.",
  )
  async def expedition_status(self, interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    data = load_pets_data()

    user_data = data.get(user_id, {})
    expedition = user_data.get("expedition")

    embed = discord.Embed(
        title="🧭 Expedition Status", color=discord.Color.blurple()
    )

    if not expedition:
      embed.description = (
          "Your pet is resting at home. Use `/expedition` to send them on an"
          " adventure!"
      )
    else:
      exp_type = expedition["type"]
      pet_name = expedition["pet_name"]
      remaining = int(expedition["finish_time"] - time.time())

      if remaining <= 0:
        embed.description = (
            f"🎉 **{pet_name}** has returned from their **{exp_type}**!\nRun"
            " **`/claim-expedition`** to collect your loot!"
        )
        embed.color = discord.Color.green()
      else:
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        time_str = (
            f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
        )
        embed.description = (
            f"🐾 **Pet:** {pet_name}\n🗺️ **Mission:** {exp_type}\n⏱️ **Time"
            f" Remaining:** {time_str}"
        )
        embed.color = discord.Color.gold()

    await interaction.response.send_message(embed=embed)

  @app_commands.command(
      name="claim-expedition",
      description="Claim rewards from your completed pet expedition.",
  )
