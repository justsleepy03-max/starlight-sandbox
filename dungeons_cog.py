import os
import json
import random
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

HEALING_POTIONS = {
    "life potion": {
        "name": "Life Potion",
        "pct": 0.50,
        "min_heal": 35,
        "desc": "Restores 50% Max HP (min 35)",
    },
}

FLOOR_GUARDIANS = [
    "Kobold Sentinel", "Ruin Stalker", "Crystal Golem", "Shadow Wolf",
    "Magma Drake", "Gale Harpy", "Frost Wyvern", "Clockwork Knight",
    "Astral Wraith", "Abyssal Knight", "Starlight Construct", "Void Chimera"
]

BOSS_FLOORS = {
    10: {"name": "Illfang the Kobold Lord", "title": "10th Floor Guardian"},
    20: {"name": "Asterius the Taurus King", "title": "20th Floor Guardian"},
    30: {"name": "Nerius the Evil Treant", "title": "30th Floor Guardian"},
    40: {"name": "Morte the Obsidian Reaver", "title": "40th Floor Guardian"},
    50: {"name": "Heathcliff's Crimson Paladin", "title": "50th Floor Mid-Spire Warden", "trophy": "coat of midnight"},
    60: {"name": "The Gleam Eyes", "title": "60th Floor Demon Boss"},
    70: {"name": "The Skull Reaper", "title": "70th Floor Scythe Sovereign"},
    80: {"name": "Chronos, Weaver of Rifts", "title": "80th Floor Temporal Lord"},
    90: {"name": "Celestial Seraphim", "title": "90th Floor Sanctuary Warden"},
    100: {"name": "Anincrad, Sovereign of the Starlight Spire", "title": "100th Floor Final Boss", "trophy": "elucidator"}
}

LOOT_TABLES = {
    "tier_1": ["soft bark", "ancient stone", "river pearl", "life potion", "common lootbox", "common egg"],
    "tier_2": ["sweet nectar", "crystal shard", "shadow petal", "uncommon lootbox", "dungeon key", "seed"],
    "tier_3": ["magma core", "gale feather", "everfrost ice", "dragon scale", "rare lootbox", "golden egg"],
    "tier_4": ["chrono dust", "starlight essence", "void matter", "world-tree sap", "singularity core", "epic lootbox", "celestial egg"]
}

# Exact scaling table for NG+1 through NG+5, with smooth uncapped escalation beyond NG+5
NG_PLUS_SCALING = {
    0: {"atk": 1.00, "hp": 1.00, "reward": 1.00},
    1: {"atk": 1.35, "hp": 1.25, "reward": 1.20},
    2: {"atk": 1.70, "hp": 1.55, "reward": 1.40},
    3: {"atk": 2.10, "hp": 1.90, "reward": 1.65},
    4: {"atk": 2.55, "hp": 2.30, "reward": 1.90},
    5: {"atk": 3.00, "hp": 2.75, "reward": 2.15},
}


def get_ng_multipliers(ng_tier: int) -> dict:
    """Returns enemy ATK, enemy HP, and reward multipliers for the given NG+ tier."""
    if ng_tier <= 0:
        return NG_PLUS_SCALING[0]
    if ng_tier in NG_PLUS_SCALING:
        return NG_PLUS_SCALING[ng_tier]
    extra_tiers = ng_tier - 5
    return {
        "atk": round(3.00 + (extra_tiers * 0.45), 2),
        "hp": round(2.75 + (extra_tiers * 0.45), 2),
        "reward": round(2.15 + (extra_tiers * 0.25), 2),
    }


def format_ng_label(ng_tier: int) -> str:
    return "Normal" if ng_tier <= 0 else f"NG+{ng_tier}"


def get_tier_cleared_floor(player_data: dict, ng_tier: int) -> int:
    """Returns highest floor cleared on the active NG+ tier (preserves legacy dungeon_floor for Normal)."""
    if ng_tier <= 0:
        return int(player_data.get("dungeon_floor", 0))
    ng_floors = player_data.get("spire_ng_floors", {})
    if not isinstance(ng_floors, dict):
        return 0
    return int(ng_floors.get(str(ng_tier), 0))


def set_tier_cleared_floor(player_data: dict, ng_tier: int, floor_num: int):
    floor_num = min(100, max(0, int(floor_num)))
    if ng_tier <= 0:
        if floor_num > int(player_data.get("dungeon_floor", 0)):
            player_data["dungeon_floor"] = floor_num
    else:
        ng_floors = player_data.setdefault("spire_ng_floors", {})
        key = str(ng_tier)
        if floor_num > int(ng_floors.get(key, 0)):
            ng_floors[key] = floor_num


def get_pet_combat_bonus(user_id: str) -> float:
    """Returns a damage multiplier based on the player's active pet."""
    if not os.path.exists(PETS_FILE):
        return 1.0
    try:
        with open(PETS_FILE, "r") as f:
            data = json.load(f)
        active_pet = data.get(str(user_id), {}).get("active_pet")
        if not active_pet:
            return 1.0
        pet_name = active_pet.get("name", "")
        if "Celestial" in pet_name:
            return 1.25  # +25% damage
        elif "Dragon" in pet_name or "Golden" in pet_name:
            return 1.15  # +15% damage
        return 1.05      # +5% damage for any active companion
    except Exception:
        return 1.0


class PotionSelect(discord.ui.Select):
    def __init__(self, combat_view, main_message, owned_potions):
        self.combat_view = combat_view
        self.main_message = main_message
        options = []
        for key, qty in owned_potions[:25]:
            meta = HEALING_POTIONS[key]
            opt = discord.SelectOption(
                label=f"{meta['name']} (x{qty})",
                value=key,
                description=meta["desc"],
                emoji="🧪"
            )
            options.append(opt)
        super().__init__(placeholder="Select a potion to use...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        meta = HEALING_POTIONS[key]
        player_data = get_player(self.combat_view.user_id)
        inv = player_data.setdefault("inventory", {})

        if inv.get(key, 0) < 1:
            await interaction.response.edit_message(
                content=f"❌ You don't have any **{meta['name']}** left in your bag!",
                view=None
            )
            return

        inv[key] -= 1
        if inv[key] <= 0:
            del inv[key]

        max_hp = player_data.get("max_hp", 100)
        cur_hp = player_data.get("hp", max_hp)
        heal_amt = max(meta["min_heal"], int(max_hp * meta["pct"]))
        player_data["hp"] = min(max_hp, cur_hp + heal_amt)
        update_player(self.combat_view.user_id, player_data)

        self.combat_view.combat_log.append(f"🧪 You drank a **{meta['name']}** and restored **{heal_amt:,} HP**!")
        await self.main_message.edit(embed=self.combat_view.build_combat_embed(player_data), view=self.combat_view)
        await interaction.response.edit_message(content=f"✅ Used **{meta['name']}** (+{heal_amt:,} HP)!", view=None)


class PotionSelectView(discord.ui.View):
    def __init__(self, combat_view, main_message, owned_potions):
        super().__init__(timeout=60)
        self.add_item(PotionSelect(combat_view, main_message, owned_potions))


class DungeonCombatView(discord.ui.View):
    def __init__(
        self,
        user_id: str,
        floor: int,
        ng_tier: int,
        enemy_name: str,
        enemy_hp: int,
        enemy_max_hp: int,
        enemy_atk: int,
        is_boss: bool,
    ):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.floor = floor
        self.ng_tier = ng_tier
        self.enemy_name = enemy_name
        self.enemy_hp = enemy_hp
        self.enemy_max_hp = enemy_max_hp
        self.enemy_atk = enemy_atk
        self.is_boss = is_boss
        tier_tag = f" [{format_ng_label(ng_tier)}]" if ng_tier > 0 else ""
        self.combat_log = [f"⚔️ **Floor {floor}{tier_tag}** battle started against **{enemy_name}**!"]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This isn't your dungeon run! Start your own with `/dungeon`.", ephemeral=True)
            return False
        return True

    def build_combat_embed(self, player_data: dict, status_color=discord.Color.red()) -> discord.Embed:
        p_max_hp = player_data.get("max_hp", 100)
        p_hp = max(0, player_data.get("hp", p_max_hp))
        inv = player_data.get("inventory", {})
        potions = sum(inv.get(k, 0) for k in HEALING_POTIONS)
        sword_tier = player_data.get("sword_tier", 1)
        armor_tier = player_data.get("armor_tier", 1)

        title_prefix = "👑 BOSS FLOOR" if self.is_boss else "🏰 TOWER FLOOR"
        tier_badge = f" [{format_ng_label(self.ng_tier)}]" if self.ng_tier > 0 else ""
        embed = discord.Embed(
            title=f"{title_prefix} {self.floor}{tier_badge} — {self.enemy_name}",
            color=status_color
        )
        embed.add_field(
            name=f"👹 {self.enemy_name}",
            value=f"❤️ **HP:** {max(0, self.enemy_hp):,} / {self.enemy_max_hp:,}\n💥 **ATK:** ~{self.enemy_atk:,}",
            inline=True
        )
        embed.add_field(
            name="🛡️ Your Status",
            value=f"❤️ **HP:** {p_hp:,} / {p_max_hp:,}\n⚔️ **Sword:** Tier {sword_tier} | 🛡️ **Armor:** Tier {armor_tier}\n🧪 **Potions:** {potions}",
            inline=True
        )
        recent_logs = "\n".join(self.combat_log[-4:])
        embed.add_field(name="📜 Combat Log", value=recent_logs, inline=False)
        embed.set_footer(text=f"Starlight 100-Floor Spire ({format_ng_label(self.ng_tier)}) • Choose your action below")
        return embed
