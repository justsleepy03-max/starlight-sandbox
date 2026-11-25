import os
import json
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player
from items import ARMORS, SWORDS

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")
DAILY_COOLDOWN_SECONDS = 24 * 60 * 60
DAILY_COIN_REWARD = 500

HEALING_ITEMS = {
    "minor hp bottle": {"heal": 35, "max_hp_boost": 0},
    "greater hp bottle": {"heal": 120, "max_hp_boost": 0},
    "starlight elixir": {"heal": 250, "max_hp_boost": 25},
    "celestial vitality draught": {"heal": 500, "max_hp_boost": 75},
    "transcendent life flask": {"heal": 1000, "max_hp_boost": 150},
}

HEALING_PRIORITY = [
    "minor hp bottle",
    "greater hp bottle",
    "starlight elixir",
    "celestial vitality draught",
    "transcendent life flask",
]

BETA_BUNDLE_ITEMS = {
    "minor hp bottle": 5,
    "greater hp bottle": 3,
    "starlight elixir": 2,
    "celestial vitality draught": 1,
    "common lootbox": 3,
    "uncommon lootbox": 2,
    "rare lootbox": 2,
    "epic lootbox": 1,
    "golden egg": 1,
    "wood": 25,
    "fish": 20,
    "iron ore": 15,
    "soft bark": 10,
    "ancient stone": 10,
    "river pearl": 10,
    "sweet nectar": 10,
    "crystal shard": 10,
}


def load_pets_data():
    if not os.path.exists(PETS_FILE):
        return {}
    try:
        with open(PETS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def get_cooldown_multiplier(user_id):
    """Checks user's active pet and returns cooldown multiplier (e.g. 0.90 for -10%)."""
    data = load_pets_data()
    user_data = data.get(str(user_id), {})
    active_pet = user_data.get("active_pet")

    if not active_pet:
        return 1.0

    pet_name = active_pet.get("name")
    if pet_name == "Starlight Celestial Spirit":
        return 0.90  # -10% cooldown
    elif pet_name == "Shadow Mouse":
        return 0.99  # -1% cooldown

    return 1.0


def _get_owned_gear_tiers(p: dict, slot: str, current_tier: int) -> list:
    """Return sorted gear tiers the player owns or has crafted, plus current_tier."""
    if not isinstance(p, dict):
        return [current_tier] if current_tier else []

    catalog = SWORDS if slot == "weapon" else ARMORS
    inv = p.get("inventory") if isinstance(p.get("inventory"), dict) else {}

    list_keys = (
        ["owned_swords", "crafted_swords", "unlocked_swords", "swords"]
        if slot == "weapon"
        else ["owned_armors", "crafted_armors", "unlocked_armors", "armors"]
    )
    max_keys = (
        ["max_sword_tier", "highest_sword_tier", "sword_tier"]
        if slot == "weapon"
        else ["max_armor_tier", "highest_armor_tier", "armor_tier"]
    )

    allowed = {int(current_tier)} if int(current_tier) in catalog else set()

    for key in list_keys:
        raw_list = p.get(key)
        if isinstance(raw_list, (list, tuple, set)):
            for entry in raw_list:
                if isinstance(entry, int) and entry in catalog:
                    allowed.add(entry)
                elif isinstance(entry, str) and entry.strip().isdigit():
                    tier_num = int(entry.strip())
                    if tier_num in catalog:
                        allowed.add(tier_num)
                elif isinstance(entry, dict):
                    t_val = entry.get("tier")
                    if isinstance(t_val, int) and t_val in catalog:
                        allowed.add(t_val)
        elif isinstance(raw_list, dict):
            for k, v in raw_list.items():
                if v and str(k).isdigit():
                    tier_num = int(k)
                    if tier_num in catalog:
                        allowed.add(tier_num)

    for key in max_keys:
        val = p.get(key)
        if isinstance(val, int) and val >= 1:
            for t_num in range(1, min(val, max(catalog.keys())) + 1):
                if t_num in catalog:
                    allowed.add(t_num)

    for tier, data in catalog.items():
        item_name = str(data.get("name", "")).strip().lower()
        if item_name and int(inv.get(item_name, 0)) > 0:
            allowed.add(tier)

    return sorted(allowed)


QUEST_POOL = [
    {"id": "hunt_monsters", "title": "Monster Slayer", "desc": "Hunt 5 times in the wild", "target": 5, "type": "hunt", "reward_coins": 500, "reward_xp": 500, "min_area": 1},
    {"id": "gather_wood", "title": "Lumberjack Duty", "desc": "Collect 15 Wood", "target": 15, "type": "chop", "reward_coins": 500, "reward_xp": 400, "min_area": 1},
    {"id": "catch_fish", "title": "Master Angler", "desc": "Catch 10 Fish", "target": 10, "type": "fish", "reward_coins": 500, "reward_xp": 400, "min_area": 1},
    {"id": "mine_ore", "title": "Master Miner", "desc": "Mine 10 Iron Ore", "target": 10, "type": "mine", "reward_coins": 500, "reward_xp": 600, "min_area": 5},
    {"id": "forge_gear", "title": "Master Blacksmith", "desc": "Craft or upgrade your gear", "target": 1, "type": "craft", "reward_coins": 500, "reward_xp": 1000, "min_area": 2},
]

AREA_BIOMES = {
    1: {"name": "Whispering Woods", "drop": "soft bark"},
    2: {"name": "Crumbling Ruins", "drop": "ancient stone"},
    3: {"name": "Sunken Riverbank", "drop": "river pearl"},
    4: {"name": "Glimmering Meadows", "drop": "sweet nectar"},
    5: {"name": "Crystal Caverns", "drop": "crystal shard"},
    6: {"name": "Shadowed Thicket", "drop": "shadow petal"},
    7: {"name": "Volcanic Caldera", "drop": "magma core"},
    8: {"name": "Whispering Windplains", "drop": "gale feather"},
    9: {"name": "Frozen Tundra", "drop": "everfrost ice"},
    10: {"name": "Dragon’s Spire", "drop": "dragon scale"},
    11: {"name": "Temporal Rift", "drop": "chrono dust"},
    12: {"name": "Celestial Sanctuary", "drop": "starlight essence"},
    13: {"name": "Abyssal Depths", "drop": "void matter"},
    14: {"name": "Mythic Overgrowth", "drop": "world-tree sap"},
    15: {"name": "The Transcendence Core", "drop": "singularity core"},
}

AREA_UNLOCKS = {
    1: "Default: /hunt, /adventure, /gather wood, /gather fish, /shop, /inventory, /quest view",
    2: "/enchant, /area, /training",
    3: "/axe, /net, /pickup",
    4: "/ladder, /guild, /farm",
    5: "/gather mine, /multidice, /cook, /casino",
    6: "/bowsaw, /boat, /pickaxe",
    7: "/refine, /big arena, /alchemy",
    8: "/tractor, /wheel",
    9: "/chainsaw, /bigboat",
    10: "/drill, /minintboss",
    11: "/time travel, /forge, /greenhouse",
    12: "/dynamite, /pets, /petadventure, /ultraining, /badge",
    13: "/transmute, /hardmode hunt",
    14: "/hardmode adventure, /big dice",
    15: "/time jump, /transcend",
}

AREA_LEVEL_REQUIREMENTS = {
    1: 1, 2: 3, 3: 6, 4: 9, 5: 12, 6: 15, 7: 18, 8: 21, 9: 24, 10: 27, 11: 30, 12: 33, 13: 36, 14: 39, 15: 42,
}


# --- INTERACTIVE VIEWS & MODALS ---
class GearSelect(discord.ui.Select):
    def __init__(self, cog, user_id: str, slot: str, current_tier: int, allowed_tiers=None):
        self.cog = cog
        self.user_id = user_id
        self.slot = slot  # "weapon" or "armor"

        catalog = SWORDS if slot == "weapon" else ARMORS
        player_data = get_player(user_id)
        tiers_to_show = allowed_tiers if allowed_tiers is not None else _get_owned_gear_tiers
