import json
import os
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
        return 0.90
    if pet_name == "Shadow Mouse":
        return 0.99

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
    10: {"name": "Dragon\u2019s Spire", "drop": "dragon scale"},
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
    1: 1,
    2: 3,
    3: 6,
    4: 9,
    5: 12,
    6: 15,
    7: 18,
    8: 21,
    9: 24,
    10: 27,
    11: 30,
    12: 33,
    13: 36,
    14: 39,
    15: 42,
}


# --- INTERACTIVE VIEWS & MODALS ---
class GearSelect(discord.ui.Select):
    def __init__(self, cog, user_id: str, slot: str, current_tier: int, allowed_tiers=None):
        self.cog = cog
        self.user_id = user_id
        self.slot = slot

        catalog = SWORDS if slot == "weapon" else ARMORS
        player_data = get_player(user_id)
        tiers_to_show = (
            allowed_tiers
            if allowed_tiers is not None
            else _get_owned_gear_tiers(player_data, slot, current_tier)
        )

        options = []
        for tier in tiers_to_show:
            data = catalog.get(tier)
            if not data:
                continue
            name = str(data.get("name", f"Tier {tier}")).title()
            stat_label = (
                f"AT {data.get('at', tier)}"
                if slot == "weapon"
                else f"DEF {data.get('def', 0)}"
            )
            is_equipped = tier == current_tier
            desc = f"Equipped \u2022 {stat_label}" if is_equipped else f"Owned/Crafted \u2022 {stat_label}"
            options.append(
                discord.SelectOption(
                    label=f"T{tier}: {name}"[:100],
                    value=str(tier),
                    description=desc[:100],
                    emoji="\u2705" if is_equipped else ("\u2694\ufe0f" if slot == "weapon" else "\U0001f6e1\ufe0f"),
                    default=is_equipped,
                )
            )

        if not options:
            fallback_tier = current_tier if current_tier in catalog else 1
            data = catalog.get(fallback_tier, {})
            name = str(data.get("name", f"Tier {fallback_tier}")).title()
            options.append(
                discord.SelectOption(
                    label=f"T{fallback_tier}: {name}"[:100],
                    value=str(fallback_tier),
                    description="No extra owned/crafted tiers unlocked yet"[:100],
                    emoji="\u2694\ufe0f" if slot == "weapon" else "\U0001f6e1\ufe0f",
                    default=True,
                )
            )

        placeholder = (
            "Choose an owned/crafted sword to equip..."
            if slot == "weapon"
            else "Choose an owned/crafted armor to equip..."
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
                "\u274c This gear menu doesn't belong to you! Use `/profile` to open your own.",
                ephemeral=True,
            )
            return

        chosen_tier = int(self.values[0])
        p = get_player(self.user_id)
        if not isinstance(p, dict) or not p:
            await interaction.response.send_message("\u274c No RPG profile found yet.", ephemeral=True)
            return

        slot_key = "sword_tier" if self.slot == "weapon" else "armor_tier"
        current_tier = int(p.get(slot_key, 1))
        allowed_tiers = _get_owned_gear_tiers(p, self.slot, current_tier)

        if chosen_tier not in allowed_tiers:
            gear_label = "sword/weapon" if self.slot == "weapon" else "armor"
            await interaction.response.send_message(
                f"\u274c You don't own or craft **Tier {chosen_tier}** {gear_label}! Buy or forge it first.",
                ephemeral=True,
            )
            return

        if self.slot == "weapon":
            data = SWORDS.get(chosen_tier)
            if not data:
                await interaction.response.send_message("\u274c Invalid weapon tier.", ephemeral=True)
                return
            origin = p.get("sword_origin", "shop")
            p["sword_tier"] = chosen_tier
            p["sword_origin"] = origin
            update_player(self.user_id, p)
            perk = " (+15% Hunt Coins)" if origin == "crafted" else ""
            item_title = data["name"].title()
            msg = f"\u2694\ufe0f Equipped **Tier {chosen_tier}: {item_title}** `[{origin.upper()}]`{perk}!"
        else:
            data = ARMORS.get(chosen_tier)
            if not data:
                await interaction.response.send_message("\u274c Invalid armor tier.", ephemeral=True)
                return
            origin = p.get("armor_origin", "shop")
            p["armor_tier"] = chosen_tier
            p["armor_origin"] = origin
            update_player(self.user_id, p)
            perk = " (+25% Gathering Yield)" if origin == "crafted" else ""
            item_title = data["name"].title()
            msg = f"\U0001f6e1\ufe0f Equipped **Tier {chosen_tier}: {item_title}** `[{origin.upper()}]`{perk}!"

        await interaction.response.edit_message(content=msg, view=None)


class GearSelectView(discord.ui.View):
    def __init__(self, cog, user_id: str, slot: str, current_tier: int, allowed_tiers=None):
        super().__init__(timeout=12
