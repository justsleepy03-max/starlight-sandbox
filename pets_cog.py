import os
import json
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

# Ensure persistent data directory exists
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


# Incubation durations in seconds
HATCH_TIMES = {
    "Common Egg": 15 * 60,            # 15 minutes
    "Golden Egg": 2 * 60 * 60,        # 2 hours
    "Celestial Egg": 6 * 60 * 60,     # 6 hours
    "Void Egg": 4 * 60 * 60,          # 4 hours
    "Transcendent Egg": 12 * 60 * 60  # 12 hours
}

# Expedition Durations and Rewards
EXPEDITION_TYPES = {
    "Short Patrol": {"duration": 30 * 60, "base_coins": 500, "material_chance": 0.3},
    "Deep Forest Hunt": {"duration": 2 * 60 * 60, "base_coins": 3000, "material_chance": 0.6},
    "Celestial Void Raid": {"duration": 6 * 60 * 60, "base_coins": 12000, "material_chance": 0.9}
}

# Pet Roster Definitions (Existing + Expansion Lineup)
PET_DATABASE = {
    "Starlight Slime": {"rarity": "Common", "type": "Common Egg", "buff_desc": "+2% Coin bonus on commands", "buff_type": "coin", "value": 0.02},
    "Pebble Crab": {"rarity": "Common", "type": "Common Egg", "buff_desc": "+1 Defense in quests", "buff_type": "defense", "value": 1},
    "Shadow Mouse": {"rarity": "Common", "type": "Common Egg", "buff_desc": "-1% cooldown reduction", "buff_type": "cooldown", "value": 0.01},

    "Sunwing Finch": {"rarity": "Uncommon", "type": "Golden Egg", "buff_desc": "+5% Expedition speed", "buff_type": "expedition", "value": 0.05},
    "Crystal Hedgehog": {"rarity": "Uncommon", "type": "Golden Egg", "buff_desc": "+5% chance to find bonus crafting materials", "buff_type": "materials", "value": 0.05},
    "Ember Fox": {"rarity": "Rare", "type": "Golden Egg", "buff_desc": "+10% Attack power during RPG battles", "buff_type": "attack", "value": 10},
    "Glowtail Panther": {"rarity": "Rare", "type": "Golden Egg", "buff_desc": "+8% Coin bonus", "buff_type": "coin", "value": 0.08},

    "Astral Phoenix": {"rarity": "Epic", "type": "Celestial Egg", "buff_desc": "5% chance to avoid failure on hard quests", "buff_type": "revive", "value": 0.05},
    "Void Turtle": {"rarity": "Epic", "type": "Celestial Egg", "buff_desc": "+15% defense and massive material yield on expeditions", "buff_type": "defense_material", "value": 0.15},
    "Nebula Dragon": {"rarity": "Legendary", "type": "Celestial Egg", "buff_desc": "+25% total coin multiplier & +15 attack power", "buff_type": "coin_attack", "value": (0.25, 15)},
    "Starlight Celestial Spirit": {"rarity": "Legendary", "type": "Celestial Egg", "buff_desc": "-10% cooldown reduction (+Coin gain & double rare drops)", "buff_type": "cooldown_ultimate", "value": 0.10},

    "Mossy Badger": {"rarity": "Common", "type": "Common Egg", "buff_desc": "-3% cooldown reduction, +5% gathering yield", "buff_type": "cooldown_gathering", "value": (0.03, 0.05)},
    "Tidepool Crab": {"rarity": "Uncommon", "type": "Common Egg", "buff_desc": "-4% cooldown reduction, +8% fish/pearl drop chance", "buff_type": "cooldown_fishing", "value": (0.04, 0.08)},
    "Sunbeam Fox": {"rarity": "Uncommon", "type": "Golden Egg", "buff_desc": "-6% cooldown reduction, +5% coin payout", "buff_type": "cooldown_coin", "value": (0.06, 0.05)},
    "Glimmer Owl": {"rarity": "Rare", "type": "Golden Egg", "buff_desc": "-7% cooldown reduction, +5% XP gain", "buff_type": "cooldown_xp", "value": (0.07, 0.05)},
    "Cinder Lynx": {"rarity": "Rare", "type": "Golden Egg", "buff_desc": "-9% cooldown reduction, +3% crit chance", "buff_type": "cooldown_crit", "value": (0.09, 0.03)},
    "Tempest Drake": {"rarity": "Epic", "type": "Celestial Egg", "buff_desc": "-12% cooldown reduction, +8% coins & +5% XP", "buff_type": "cooldown_coin_xp", "value": (0.12, 0.08, 0.05)},
    "Aether Phoenix": {"rarity": "Mythic", "type": "Celestial Egg", "buff_desc": "-14% cooldown reduction, +5% crit & HP recovery boost", "buff_type": "cooldown_crit_heal", "value": (0.14, 0.05, 0.05)},
    "Singularity Kitsune": {"rarity": "Void", "type": "Celestial Egg", "buff_desc": "-15% cooldown reduction, +6% crit & +10% rare drop chance", "buff_type": "cooldown_crit_rare", "value": (0.15, 0.06, 0.10)},
    "Abyssal Stalker": {"rarity": "Abyssal", "type": "Void Egg
