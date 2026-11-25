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
    15: {"name": "The Transcendence Core", "drop": "singularity core"}
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
    15: "/time jump, /transcend"
}

AREA_LEVEL_REQUIREMENTS = {
    1: 1, 2: 3, 3: 6, 4: 9, 5: 12, 6: 15, 7: 18, 8: 21, 9: 24, 10: 27, 11: 30, 12: 33, 13: 36, 14: 39, 15: 42
}

# --- INTERACTIVE VIEWS & MODALS ---
class GearSelect(discord.ui.Select):
    def __init__(self, cog, user_id: str, slot: str, current_tier: int):
        self.cog = cog
        self.user_id = user_id
        self.slot = slot  # "weapon" or "armor"

        catalog = SWORDS if slot == "weapon" else ARMORS
        options = []
        for tier, data in catalog.items():
            name = str(data.get("name", f"Tier {tier}")).title()
            stat_label = (
                f"AT {data.get('at', tier)}"
                if slot == "weapon"
                else f"DEF {data.get('def', 0)}"
            )
            is_equipped = tier == current_tier
            options.append(
                discord.SelectOption(
                    label=f"T{tier}: {name}"[:100],
                    value=str(tier),
                    description=(f"Equipped • {stat_label}" if is_equipped else stat_label)[:100],
                    emoji="✅" if is_equipped else ("⚔️" if slot == "weapon" else "🛡️"),
                    default=is_equipped,
                )
            )

        placeholder = (
            "Choose a sword/weapon tier to equip..."
            if slot == "weapon"
            else "Choose an armor tier to equip..."
        )
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id=f"rpg_select_{slot}",
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This gear menu doesn't belong to you! Use `/profile` to open your own.",
                ephemeral=True,
            )
            return

        chosen_tier = int(self.values[0])
        p = get_player(self.user_id)
        if not isinstance(p, dict) or not p:
            await interaction.response.send_message("❌ No RPG profile found yet.", ephemeral=True)
            return

        if self.slot == "weapon":
            data = SWORDS.get(chosen_tier)
            if not data:
                await interaction.response.send_message("❌ Invalid weapon tier.", ephemeral=True)
                return
            origin = p.get("sword_origin", "shop")
            p["sword_tier"] = chosen_tier
            p["sword_origin"] = origin
            update_player(self.user_id, p)
            perk = " (+15% Hunt Coins)" if origin == "crafted" else ""
            msg = f"⚔️ Equipped **Tier {chosen_tier}: {data['name'].title()}** `[{origin.upper()}]`{perk}!"
        else:
            data = ARMORS.get(chosen_tier)
            if not data:
                await interaction.response.send_message("❌ Invalid armor tier.", ephemeral=True)
                return
            origin = p.get("armor_origin", "shop")
            p["armor_tier"] = chosen_tier
            p["armor_origin"] = origin
            update_player(self.user_id, p)
            perk = " (+25% Gathering Yield)" if origin == "crafted" else ""
            msg = f"🛡️ Equipped **Tier {chosen_tier}: {data['name'].title()}** `[{origin.upper()}]`{perk}!"

        await interaction.response.edit_message(content=msg, view=None)


class GearSelectView(discord.ui.View):
    def __init__(self, cog, user_id: str, slot: str, current_tier: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(GearSelect(cog, user_id, slot, current_tier))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await
