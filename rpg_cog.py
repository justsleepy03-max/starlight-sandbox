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
        tiers_to_show = allowed_tiers if allowed_tiers is not None else _get_owned_gear_tiers(player_data, slot, current_tier)

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
            desc = f"Equipped • {stat_label}" if is_equipped else f"Owned/Crafted • {stat_label}"
            options.append(
                discord.SelectOption(
                    label=f"T{tier}: {name}"[:100],
                    value=str(tier),
                    description=desc[:100],
                    emoji="✅" if is_equipped else ("⚔️" if slot == "weapon" else "🛡️"),
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
                    emoji="⚔️" if slot == "weapon" else "🛡️",
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
                "❌ This gear menu doesn't belong to you! Use `/profile` to open your own.",
                ephemeral=True,
            )
            return

        chosen_tier = int(self.values[0])
        p = get_player(self.user_id)
        if not isinstance(p, dict) or not p:
            await interaction.response.send_message("❌ No RPG profile found yet.", ephemeral=True)
            return

        slot_key = "sword_tier" if self.slot == "weapon" else "armor_tier"
        current_tier = int(p.get(slot_key, 1))
        allowed_tiers = _get_owned_gear_tiers(p, self.slot, current_tier)

        if chosen_tier not in allowed_tiers:
            gear_label = "sword/weapon" if self.slot == "weapon" else "armor"
            await interaction.response.send_message(
                f"❌ You don't own or craft **Tier {chosen_tier}** {gear_label}! Buy or forge it first.",
                ephemeral=True,
            )
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
            item_title = data["name"].title()
            msg = f"⚔️ Equipped **Tier {chosen_tier}: {item_title}** `[{origin.upper()}]`{perk}!"
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
            item_title = data["name"].title()
            msg = f"🛡️ Equipped **Tier {chosen_tier}: {item_title}** `[{origin.upper()}]`{perk}!"

        await interaction.response.edit_message(content=msg, view=None)


class GearSelectView(discord.ui.View):
    def __init__(self, cog, user_id: str, slot: str, current_tier: int, allowed_tiers=None):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(GearSelect(cog, user_id, slot, current_tier, allowed_tiers))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This gear menu doesn't belong to you! Use `/profile` to open your own.",
                ephemeral=True,
            )
            return False
        return True


class RPGActionView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This action menu doesn't belong to you! Use `/profile` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="⚔️ Hunt", style=discord.ButtonStyle.danger, custom_id="rpg_hunt")
    async def hunt_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.execute_hunt(interaction)

    @discord.ui.button(label="🗺️ Adventure", style=discord.ButtonStyle.primary, custom_id="rpg_adventure")
    async def adventure_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.execute_adventure(interaction)

    @discord.ui.button(label="🪓 Chop", style=discord.ButtonStyle.success, custom_id="rpg_chop")
    async def chop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.execute_chop(interaction)

    @discord.ui.button(label="🎣 Fish", style=discord.ButtonStyle.secondary, custom_id="rpg_fish")
    async def fish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.execute_fish(interaction)

    @discord.ui.button(label="⚔️ Sword", style=discord.ButtonStyle.secondary, custom_id="rpg_equip_sword")
    async def equip_sword_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = get_player(self.user_id)
        current_tier = int(p.get("sword_tier", 1)) if isinstance(p, dict) else 1
        allowed_tiers = _get_owned_gear_tiers(p, "weapon", current_tier)
        view = GearSelectView(self.cog, self.user_id, "weapon", current_tier, allowed_tiers)
        await interaction.response.send_message(
            "⚔️ Select an owned or crafted sword/weapon tier to equip:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="🛡️ Armor", style=discord.ButtonStyle.secondary, custom_id="rpg_equip_armor")
    async def equip_armor_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = get_player(self.user_id)
        current_tier = int(p.get("armor_tier", 1)) if isinstance(p, dict) else 1
        allowed_tiers = _get_owned_gear_tiers(p, "armor", current_tier)
        view = GearSelectView(self.cog, self.user_id, "armor", current_tier, allowed_tiers)
        await interaction.response.send_message(
            "🛡️ Select an owned or crafted armor tier to equip:",
            view=view,
            ephemeral=True,
        )


class AreaSelect(discord.ui.Select):
    def __init__(self, cog, user_id: str, current_area: int, unlocked_area: int):
        self.cog = cog
        self.user_id = user_id

        options = []
        for a_id in range(1, unlocked_area + 1):
            b_name = AREA_BIOMES.get(a_id, {}).get("name", "Unknown")
            req_lvl = AREA_LEVEL_REQUIREMENTS.get(a_id, 1)
            is_current = a_id == current_area
            options.append(
                discord.SelectOption(
                    label=f"Area {a_id}: {b_name}",
                    value=str(a_id),
                    description=f"Current location (Lv. {req_lvl}+)" if is_current else f"Travel to {b_name} (Lv. {req_lvl}+)",
                    emoji="📍" if is_current else "🧭",
                    default=is_current,
                )
            )

        super().__init__(
            placeholder="Select an unlocked area to travel to...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="area_travel_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This travel menu doesn't belong to you! Use `/area` to open your own.",
                ephemeral=True,
            )
            return

        chosen_area = int(self.values[0])
        p = get_player(self.user_id)
        unlocked = self.cog._sync_unlocked_area(p)

        if chosen_area > unlocked:
            req_lvl = AREA_LEVEL_REQUIREMENTS.get(chosen_area, 1)
            await interaction.response.send_message(
                f"🔒 **Area {chosen_area}** is locked! Reach **Level {req_lvl}** first.",
                ephemeral=True,
            )
            return

        p["area"] = chosen_area
        update_player(self.user_id, p)

        embed = self.cog.build_area_embed(p, unlocked)
        new_view = AreaTravelView(self.cog, self.user_id, chosen_area, unlocked)
        biome_name = AREA_BIOMES.get(chosen_area, {}).get("name", "Unknown Biome")
        unlock_info = AREA_UNLOCKS.get(chosen_area, "")
        unlock_line = f"
🔓 *Unlocks:* {unlock_info}" if unlock_info else ""

        await interaction.response.edit_message(embed=embed, view=new_view)
        await interaction.followup.send(
            f"🧭 Traveled to **Area {chosen_area} — {biome_name}**!{unlock_line}",
            ephemeral=True,
        )


class AreaTravelView(discord.ui.View):
    def __init__(self, cog, user_id: str, current_area: int, unlocked_area: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.add_item(AreaSelect(cog, user_id, current_area, unlocked_area))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This travel menu doesn't belong to you! Use `/area` to open your own.",
                ephemeral=True,
            )
            return False
        return True


class EconomyAmountModal(discord.ui.Modal):
    def __init__(self, cog, user_id: str, action: str, source_view):
        title = "Deposit Coins to Bank" if action == "deposit" else "Withdraw Coins to Wallet"
        super().__init__(title=title)
        self.cog = cog
        self.user_id = user_id
        self.action = action
        self.source_view = source_view

        self.amount_input = discord.ui.TextInput(
            label="Amount (or type 'all')",
            placeholder="e.g. 500 or all",
            required=True,
            max_length=20,
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This economy menu doesn't belong to you! Use `/economy` to open your own.",
                ephemeral=True,
            )
            return

        raw = self.amount_input.value.strip().lower()
        if self.action == "deposit":
            ok, msg, embed = self.cog.perform_deposit(self.user_id, raw, interaction.user.display_name)
        else:
            ok, msg, embed = self.cog.perform_withdraw(self.user_id, raw, interaction.user.display_name)

        if not ok:
            await interaction.response.send_message(msg, ephemeral=True)
            return

        await interaction.response.edit_message(embed=embed, view=self.source_view)
        await interaction.followup.send(msg, ephemeral=True)


class EconomyView(discord.ui.View):
    def __init__(self, cog, user_id: str):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This economy menu doesn't belong to you! Use `/economy` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="💰 Balance", style=discord.ButtonStyle.primary, custom_id="econ_bal")
    async def balance_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.build_balance_embed(self.user_id, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🏦 Deposit", style=discord.ButtonStyle.success, custom_id="econ_deposit")
    async def deposit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EconomyAmountModal(self.cog, self.user_id, "deposit", self))

    @discord.ui.button(label="💸 Withdraw", style=discord.ButtonStyle.secondary, custom_id="econ_withdraw")
    async def withdraw_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EconomyAmountModal(self.cog, self.user_id, "withdraw", self))


class HelpView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This help menu doesn't belong to you!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="⚔️ RPG Core", style=discord.ButtonStyle.primary, custom_id="help_rpg")
    async def rpg_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="✨ Starlight Sandbox - RPG Core Commands", color=discord.Color.blurple())
        embed.add_field(
            name="Actions & Hub",
            value=(
                "`/profile` - View stats & action hub\n"
                "`/hunt` - Hunt monsters in current biome\n"
                "`/adventure` - Embark on an epic adventure\n"
                "`/gather wood` / `fish` / `mine` - Gather resources in your biome\n"
                "`/heal` - Use potions or life boosts to recover HP"
            ),
            inline=False,
        )
        embed.add_field(
            name="Progression & Economy",
            value=(
                "`/area` - View biomes/unlocks or travel via dropdown menu\n"
                "`/inventory` - Check items & materials\n"
                "`/economy` - Balance, deposit & withdraw button hub\n"
                "`/daily` - Claim daily coins\n"
                "`/open` - Open loot boxes\n"
                "`/quest view` / `claim` / `abandon` - Manage quests\n"
                "`/givebundle` - Owner-only beta bundle reward command"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🗺️ Area Expansions", style=discord.ButtonStyle.success, custom_id="help_areas")
    async def areas_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🗺️ Starlight Sandbox - Area Expansions (Areas 2–15)", color=discord.Color.green())
        embed.add_field(name="Early Biomes (Areas 2–6)", value="`/enchant`, `/training`, `/axe`, `/net`, `/pickup`, `/ladder`, `/farm`, `/multidice`, `/cook`, `/casino`, `/bowsaw`, `/boat`, `/pickaxe`", inline=False)
        embed.add_field(name="Mid-High Biomes (Areas 7–12)", value="`/refine`, `/big_arena`, `/alchemy`, `/tractor`, `/wheel`, `/chainsaw`, `/bigboat`, `/drill`, `/minintboss`, `/time_travel`, `/temporal_forge`, `/greenhouse`, `/dynamite`, `/petadventure`, `/ultraining`, `/badge`", inline=False)
        embed.add_field(name="Endgame Biomes (Areas 13–15)", value="`/transmute`, `/hardmode hunt`, `/hardmode adventure`, `/big_dice`, `/time_jump`, `/transcend`", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎉 Party Games", style=discord.ButtonStyle.secondary, custom_id="help_party")
    async def party_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎉 Starlight Sandbox - Party Games Suite", color=discord.Color.gold())
        embed.add_field(name="Interactive Games", value="`/cah` - Play Cards Against Humanity with buttons\n`/trivia` - Test knowledge with interactive buttons\n`/connect4` - Play Connect Four board with column buttons\n`/bingo` - Generate a community Bingo card", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)


class RpgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    quest_group = app_commands.Group(
        name="quest",
        description="View, claim, or abandon your active RPG quest.",
    )

    gather_group = app_commands.Group(
        name="gather",
        description="Gather wood, fish, or mine ore in your current biome.",
    )

    hardmode_group = app_commands.Group(
        name="hardmode",
        description="High-risk, high-reward hardmode hunts and adventures (Area 13+).",
    )

    def _sync_unlocked_area(self, p: dict) -> int:
        level = int(p.get("level", 1))
        unlocked = int(p.get("unlocked_area", p.get("area", 1)))
        eligible = 1
        for area_id, req_level in AREA_LEVEL_REQUIREMENTS.items():
            if level >= req_level:
                eligible = area_id
        if eligible > unlocked:
            unlocked = eligible
            p["unlocked_area"] = unlocked
        return unlocked

    def build_area_embed(self, p: dict, unlocked: int) -> discord.Embed:
        current_area = int(p.get("area", 1))
        current_biome = AREA_BIOMES.get(current_area, {}).get("name", "Unknown")
        lines = []
        for a_id in range(1, 16):
            b_name = AREA_BIOMES.get(a_id, {}).get("name", "Unknown")
            req_lvl = AREA_LEVEL_REQUIREMENTS.get(a_id, 1)
            marker = "📍 " if a_id == current_area else ("✅ " if a_id <= unlocked else "🔒 ")
            lines.append(f"{marker}**Area {a_id}:** {b_name} *(Lv. {req_lvl}+)*")

        embed = discord.Embed(
            title="🗺️ Biomes & Area Travel",
            description="
".join(lines),
            color=discord.Color.green(),
        )
        embed.add_field(
            name="Current Location",
            value=f"Area {current_area} (**{current_biome}**) • Highest Unlocked: **Area {unlocked}**",
            inline=False,
        )
        embed.set_footer(text="Select an unlocked biome from the dropdown menu below to travel!")
        return embed

    def _update_quest_progress(self, p, action_type, amount=1):
        active = p.get("active_quest")
        if active and active["type"] == action_type and active["progress"] < active["target"]:
            active["progress"] = min(active["target"], active["progress"] + amount)

    def _advance_biome_quest(self, p, action_type, amount=1):
        bq = p.get("active_biome_quest")
        if not isinstance(bq, dict):
            return
        if bq.get("type") != action_type:
            return
        if action_type != "craft" and p.get("area", 1) != bq.get("area"):
            return
        target = int(bq.get("target", 1))
        bq["progress"] = min(target, int(bq.get("progress", 0)) + amount)

    def _check_level_up(self, p):
        xp_needed = p["level"] * 250
        messages = []

        while p["xp"] >= xp_needed:
            p["xp"] -= xp_needed
            p["level"] += 1
            p["max_hp"] += 20
            p["hp"] = p["max_hp"]
            messages.append(f"
🎉 **LEVEL UP!** You reached **Level {p['level']}**! Max HP increased to {p['max_hp']}.")
            xp_needed = p["level"] * 250

        current_level = p.get("level", 1)
        current_unlocked = p.get("unlocked_area", p.get("area", 1))

        highest_eligible = 1
        for area_id, req_level in AREA_LEVEL_REQUIREMENTS.items():
            if current_level >= req_level:
                highest_eligible = area_id

        if highest_eligible > current_unlocked:
            p["unlocked_area"] = highest_eligible
            new_biome_name = AREA_BIOMES.get(highest_eligible, {}).get("name", "Unknown Zone")
            messages.append(f"
🚀 **AREA UNLOCKED!** Your level progression automatically unlocked **Area {highest_eligible} ({new_biome_name})**!")

        return "".join(messages)

    def _get_gear_multipliers(self, p):
        sword_origin = p.get("sword_origin", "shop")
        armor_origin = p.get("armor_origin", "shop")

        coin_mult = 1.15 if sword_origin == "crafted" else 1.0
        gathering_mult = 1.25 if armor_origin == "crafted" else 1.0

        return coin_mult, gathering_mult

    def _calculate_enemy_damage(self, p, encounter_type="mob"):
        """50% chance to deal damage; scales with area and reduces via equipped armor defense."""
        if random.random() >= 0.50:
            return 0

        area = p.get("area", 1)
        armor_tier = p.get("armor_tier", 1)
        armor_def = ARMORS.get(armor_tier, {}).get("def", 0)

        if encounter_type == "boss":
            raw_dmg = random.randint(20, 35) * area
            mitigated = raw_dmg - int(armor_def * 0.6)
            return max(5, mitigated)
        elif encounter_type == "miniboss":
            raw_dmg = random.randint(12, 22) * area
            mitigated = raw_dmg - int(armor_def * 0.55)
            return max(3, mitigated)
        else:
            raw_dmg = random.randint(5, 12) * area
            mitigated = raw_dmg - int(armor_def * 0.5)
            return max(1, mitigated)

    def build_balance_embed(self, uid: str, display_name: str) -> discord.Embed:
        p = get_player(uid)
        wallet = p.get("wallet", 0)
        bank = p.get("bank", 0)
        embed = discord.Embed(title=f"🪙 {display_name}'s Economy Hub", color=discord.Color.gold())
        embed.add_field(
            name="Balances",
            value=f"🪙 **Wallet:** {wallet:,} coins
🏛️ **Bank:** {bank:,} coins
💎 **Total:** {wallet + bank:,} coins",
            inline=False,
        )
        embed.set_footer(text="Use the buttons below to refresh balance, deposit, or withdraw.")
        return embed

    def perform_deposit(self, uid: str, raw_amount: str, display_name: str):
        p = get_player(uid)
        wallet = p.get("wallet", 0)
        bank = p.get("bank", 0)

        if raw_amount in ("all", "max"):
            amount = wallet
        else:
            cleaned = raw_amount.replace(",", "")
            if not cleaned.isdigit():
                return False, "❌ Enter a positive number or `all`.", None
            amount = int(cleaned)

        if amount <= 0:
            return False, "❌ You don't have any coins to deposit!", None
        if amount > wallet:
            return False, f"❌ You only have **🪙 {wallet:,}** coins in your wallet!", None

        p["wallet"] = wallet - amount
        p["bank"] = bank + amount
        update_player(uid, p)
        return True, f"🏦 Deposited **🪙 {amount:,}** coins into your bank!", self.build_balance_embed(uid, display_name)

    def perform_withdraw(self, uid: str, raw_amount: str, display_name: str):
        p = get_player(uid)
        wallet = p.get("wallet", 0)
        bank = p.get("bank", 0)

        if raw_amount in ("all", "max"):
            amount = bank
        else:
            cleaned = raw_amount.replace(",", "")
            if not cleaned.isdigit():
                return False, "❌ Enter a positive number or `all`.", None
            amount = int(cleaned)

        if amount <= 0:
            return False, "❌ You don't have any coins in your bank to withdraw!", None
        if amount > bank:
            return False, f"❌ You only have **🪙 {bank:,}** coins in your bank!", None

        p["bank"] = bank - amount
        p["wallet"] = wallet + amount
        update_player(uid, p)
        return True, f"💸 Withdrew **🪙 {amount:,}** coins to your wallet!", self.build_balance_embed(uid, display_name)

    @discord.app_commands.command(name="daily", description="Claim your daily 500 coins reward (24-hour cooldown).")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        now = time.time()
        last_daily = p.get("last_daily", 0)

        try:
            last_daily_ts = float(last_daily)
        except (TypeError, ValueError):
            last_daily_ts = 0.0

        elapsed = now - last_daily_ts
        if elapsed < DAILY_COOLDOWN_SECONDS:
            remaining = int(DAILY_COOLDOWN_SECONDS - elapsed)
            hours, rem = divmod(remaining, 3600)
            minutes, seconds = divmod(rem, 60)
            await interaction.response.send_message(
                f"⏳ You've already claimed your daily reward! Come back in **{hours}h {minutes}m {seconds}s**.",
                ephemeral=True,
            )
            return

        p["last_daily"] = now
        p["wallet"] = p.get("wallet", 0) + DAILY_COIN_REWARD
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        await interaction.response.send_message(
            f"🎁 **Daily Reward Claimed!** You received **+🪙 {DAILY_COIN_REWARD:,}** coins in your wallet.{level_msg}"
        )

    @discord.app_commands.command(
        name="givebundle",
        description="Owner only: Give a custom beta tester bundle with coins and items.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        member="Beta tester to receive the bundle",
        coins="Bonus coins to add to their wallet",
        include_pack="Include the multi-item beta pack (default True)",
        bundle_name="Optional custom name for the bundle",
    )
    async def givebundle(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        coins: int = 5000,
        include_pack: bool = True,
        bundle_name: str = "Patch 4/5 Beta Tester Bundle",
    ):
        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(
                "❌ Only the bot owner can use `/givebundle`.",
                ephemeral=True,
            )
            return

        uid = str(member.id)
        p = get_player(uid)
        inv = p.setdefault("inventory", {})

        if coins > 0:
            p["wallet"] = p.get("wallet", 0) + coins

        granted_count = 0
        if include_pack:
            for item_key, qty in BETA_BUNDLE_ITEMS.items():
                if qty > 0:
                    inv[item_key.lower()] = inv.get(item_key.lower(), 0) + qty
                    granted_count += 1

        claimed = p.setdefault("claimed_beta_bundles", [])
        if bundle_name not in claimed:
            claimed.append(bundle_name)

        level_msg = self._check_level_up(p)
        update_player(uid, p)

        await interaction.response.send_message(
            f"🎁 Granted **{bundle_name}** to {member.mention}! "
            f"+🪙 **{coins:,}** coins and **{granted_count}** item types added to inventory.{level_msg}"
        )

    @discord.app_commands.command(name="economy", description="Check your balance, deposit coins, or withdraw coins using buttons.")
    async def economy(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        embed = self.build_balance_embed(uid, interaction.user.display_name)
        view = EconomyView(self, uid)
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="help", description="View all available Starlight Sandbox commands and games.")
    async def help(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        embed = discord.Embed(
            title="🌟 Starlight Sandbox - Help Hub",
            description="Select a category using the buttons below to explore the core RPG loop, area-locked expansion commands, and party games!",
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Starlight Community Bot • Button Navigation")
        view = HelpView(self, uid)
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="profile", description="Check your RPG character stats, gear, and action buttons.")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not isinstance(p, dict) or not p:
            await interaction.response.send_message(
                "❌ No RPG profile found yet. Try running a starter command like `/daily` or `/hunt` first!",
                ephemeral=True,
            )
            return

        area = int(p.get("area", 1))
        unlocked_area = int(p.get("unlocked_area", area))
        biome = AREA_BIOMES.get(area, {}).get("name", "Unknown Biome")

        sword_tier = int(p.get("sword_tier", 1))
        armor_tier = int(p.get("armor_tier", 1))
        s_origin = f"({str(p.get('sword_origin', 'shop')).upper()})"
        a_origin = f"({str(p.get('armor_origin', 'shop')).upper()})"

        sword_name = SWORDS.get(sword_tier, {}).get("name", f"Tier {sword_tier}").title()
        armor_name = ARMORS.get(armor_tier, {}).get("name", "worn leather tunic" if armor_tier == 1 else f"Tier {armor_tier}").title()

        level = int(p.get("level", 1))
        xp = int(p.get("xp", 0))
        max_hp = int(p.get("max_hp", 100))
        hp = int(p.get("hp", max_hp))
        wallet = int(p.get("wallet", 0))
        bank = int(p.get("bank", 0))

        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile & Action Hub", color=discord.Color.blurple())
        embed.add_field(
            name="PROGRESS",
            value=(
                f"**Level:** {level} ({xp:,}/{level * 250:,} XP)
"
                f"**Current Biome:** Area {area} ({biome})
"
                f"**Highest Unlocked Area:** Tier {unlocked_area}"
            ),
            inline=False,
        )
        embed.add_field(name="STATS", value=f"❤️ **HP:** {hp:,}/{max_hp:,}", inline=False)
        embed.add_field(
            name="GEAR",
            value=(
                f"⚔️ **Sword:** T{sword_tier} — {sword_name} {s_origin}
"
                f"🛡️ **Armor:** T{armor_tier} — {armor_name} {a_origin}"
            ),
            inline=False,
        )
        embed.add_field(name="CURRENCY", value=f"🪙 **Wallet:** {wallet:,}
🏛️ **Bank:** {bank:,}", inline=False)
        embed.set_footer(text="Use the interactive buttons below to play or swap your equipped sword/armor!")

        view = RPGActionView(self, uid)
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="area", description="View unlocked areas or select a biome from the dropdown to travel.")
    @app_commands.describe(area="Optional area number (1–15) to travel directly")
    async def area(self, interaction: discord.Interaction, area=None):
        uid = str(interaction.user.id)
        p = get_player(uid)
        unlocked = self._sync_unlocked_area(p)
        current_area = int(p.get("area", 1))

        if area is None:
            update_player(uid, p)
            embed = self.build_area_embed(p, unlocked)
            view = AreaTravelView(self, uid, current_area, unlocked)
            await interaction.response.send_message(embed=embed, view=view)
            return

        if area < 1 or area > 15:
            await interaction.response.send_message("❌ Choose an area between **1** and **15**.", ephemeral=True)
            return

        if area > unlocked:
            req_lvl = AREA_LEVEL_REQUIREMENTS.get(area, 1)
            await interaction.response.send_message(
                f"🔒 **Area {area}** is locked! Reach **Level {req_lvl}** (highest unlocked: **Area {unlocked}**).",
                ephemeral=True,
            )
            return

        p["area"] = area
        update_player(uid, p)
        biome_name = AREA_BIOMES.get(area, {}).get("name", "Unknown Biome")
        unlock_info = AREA_UNLOCKS.get(area, "")
        unlock_line = f"
🔓 *Unlocks:* {unlock_info}" if unlock_info else ""
        await interaction.response.send_message(f"🧭 Traveled to **Area {area} — {biome_name}**!{unlock_line}")

    @discord.app_commands.command(name="heal", description="Use a healing bottle, elixir, or life flask from your inventory to restore HP.")
    @app_commands.describe(item_name="Healing item to use (e.g. minor hp bottle, starlight elixir)", quantity="How many to use (default 1)")
    async def heal(self, interaction: discord.Interaction, item_name: str = None, quantity: int = 1):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.setdefault("inventory", {})

        if quantity < 1:
            await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
            return

        if item_name:
            chosen = item_name.lower().strip()
            if chosen not in HEALING_ITEMS:
                await interaction.response.send_message(
                    "❌ That isn't a valid healing item! Check `/shop` Page 2 for available HP bottles, elixirs, and flasks.",
                    ephemeral=True,
                )
                return
        else:
            chosen = next((k for k in HEALING_PRIORITY if inv.get(k, 0) > 0), None)
            if not chosen:
                await interaction.response.send_message(
                    "❌ You don't have any healing bottles or elixirs in your inventory! Grab some from `/shop`.",
                    ephemeral=True,
                )
                return

        owned = inv.get(chosen, 0)
        if owned < quantity:
            await interaction.response.send_message(
                f"❌ You only have **{owned}x {chosen.title()}** in your inventory!",
                ephemeral=True,
            )
            return

        stats = HEALING_ITEMS[chosen]
        inv[chosen] -= quantity
        if inv[chosen] <= 0:
            del inv[chosen]

        max_hp_gain = stats["max_hp_boost"] * quantity
        if max_hp_gain > 0:
            p["max_hp"] = p.get("max_hp", 100) + max_hp_gain

        heal_amount = stats["heal"] * quantity
        current_hp = p.get("hp", p.get("max_hp", 100))
        p["hp"] = min(p.get("max_hp", 100), current_hp + heal_amount)

        update_player(uid, p)

        boost_text = f" | 📈 **+{max_hp_gain} Max HP**" if max_hp_gain > 0 else ""
        await interaction.response.send_message(
            f"🧪 Used **{quantity}x {chosen.title()}**! Restored **+{heal_amount} HP**{boost_text} — Now at **{p['hp']}/{p['max_hp']} HP**."
        )

    @discord.app_commands.command(name="hunt", description="Hunt monsters in your current biome.")
    async def hunt(self, interaction: discord.Interaction):
        await self.execute_hunt(interaction)

    async def execute_hunt(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.setdefault("inventory", {})
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_name = biome.get("name", "Unknown Biome")
        biome_drop = biome.get("drop", "common material")

        coin_mult, _ = self._get_gear_multipliers(p)
        sword_bonus = p.get("sword_tier", 1) * 8
        earned_coins = int(((random.randint(20, 45) + sword_bonus) * area) * coin_mult)
        earned_xp = random.randint(15, 30) * area
        drop_qty = random.randint(1, 3) * area

        p["wallet"] = p.get("wallet", 0) + earned_coins
        p["xp"] = p.get("xp", 0) + earned_xp
        inv[biome_drop] = inv.get(biome_drop, 0) + drop_qty

        dmg_taken = self._calculate_enemy_damage(p, encounter_type="mob")
        max_hp = p.get("max_hp", 100)
        cur_hp = p.get("hp", max_hp)
        if dmg_taken > 0:
            p["hp"] = max(0, cur_hp - dmg_taken)
            hp_msg = f" | 💔 Took **{dmg_taken}** DMG ({p['hp']}/{max_hp} HP)"
        else:
            hp_msg = f" | 🛡️ Dodged! ({cur_hp}/{max_hp} HP)"

        self._update_quest_progress(p, "hunt", 1)
        self._advance_biome_quest(p, "hunt", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        crafted_tag = " (✨ Crafted Bonus!)" if p.get("sword_origin") == "crafted" else ""
        low_hp_tip = "
⚠️ *Low HP! Use `/heal` to patch yourself up.*" if p["hp"] <= max(10, int(p["max_hp"] * 0.25)) else ""
        await interaction.response.send_message(
            f"⚔️ **Hunt in {biome_name}**: +🪙 {earned_coins:,}{crafted_tag} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{hp_msg}{level_msg}{low_hp_tip}",
            ephemeral=False,
        )

    @discord.app_commands.command(name="adventure", description="Embark on an epic adventure in your current biome.")
    async def adventure(self, interaction: discord.Interaction):
        await self.execute_adventure(interaction)

    async def execute_adventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.setdefault("inventory", {})
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_name = biome.get("name", "Unknown Biome")
        biome_drop = biome.get("drop", "common material")

        coin_mult, _ = self._get_gear_multipliers(p)
        sword_bonus = p.get("sword_tier", 1) * 20
        earned_coins = int(((random.randint(80, 180) + sword_bonus) * area) * coin_mult)
        earned_xp = random.randint(60, 130) * area
        drop_qty = random.randint(3, 7) * area

        p["wallet"] = p.get("wallet", 0) + earned_coins
        p["xp"] = p.get("xp", 0) + earned_xp
        inv[biome_drop] = inv.get(biome_drop, 0) + drop_qty

        self._update_quest_progress(p, "adventure", 1)
        self._advance_biome_quest(p, "adventure", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        await interaction.response.send_message(
            f"🗺️ **Adventure in {biome_name}**: +🪙 {earned_coins:,} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{level_msg}",
            ephemeral=False,
        )

    # --- GATHERING COMMANDS & PROFILE BUTTON HANDLERS ---
    async def execute_chop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.setdefault("inventory", {})
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_name = biome.get("name", "Unknown Biome")
        biome_drop = biome.get("drop", "soft bark")

        _, gather_mult = self._get_gear_multipliers(p)
        wood_qty = max(1, int(random.randint(3, 6) * area * gather_mult))
        bonus_qty = max(1, int(random.randint(1, 2) * gather_mult))
        earned_xp = random.randint(10, 22) * area

        inv["wood"] = inv.get("wood", 0) + wood_qty
        inv[biome_drop] = inv.get(biome_drop, 0) + bonus_qty
        p["xp"] = p.get("xp", 0) + earned_xp

        self._update_quest_progress(p, "chop", wood_qty)
        self._advance_biome_quest(p, "chop", wood_qty)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        crafted_tag = " (✨ Crafted Armor Bonus!)" if p.get("armor_origin") == "crafted" else ""
        await interaction.response.send_message(
            f"🪓 **Chopped in {biome_name}**: +{wood_qty}x Wood | +{bonus_qty}x {biome_drop.title()}{crafted_tag} | +⭐ {earned_xp:,} XP{level_msg}",
            ephemeral=False,
        )

    async def execute_fish(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.setdefault("inventory", {})
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_name = biome.get("name", "Unknown Biome")
        biome_drop = biome.get("drop", "river pearl")

        _, gather_mult = self._get_gear_multipliers(p)
        fish_qty = max(1, int(random.randint(2, 5) * area * gather_mult))
        bonus_qty = max(1, int(random.randint(1, 2) * gather_mult))
        earned_xp = random.randint(10, 22) * area

        inv["fish"] = inv.get("fish", 0) + fish_qty
        inv[biome_drop] = inv.get(biome_drop, 0) + bonus_qty
        p["xp"] = p.get("xp", 0) + earned_xp

        self._update_quest_progress(p, "fish", fish_qty)
        self._advance_biome_quest(p, "fish", fish_qty)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        crafted_tag = " (✨ Crafted Armor Bonus!)" if p.get("armor_origin") == "crafted" else ""
        await interaction.response.send_message(
            f"🎣 **Fished in {biome_name}**: +{fish_qty}x Fish | +{bonus_qty}x {biome_drop.title()}{crafted_tag} | +⭐ {earned_xp:,} XP{level_msg}",
            ephemeral=False,
        )

    async def execute_mine(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        if area < 5:
            await interaction.response.send_message(
                "❌ Mining unlocks in **Area 5 (Crystal Caverns)** or higher!",
                ephemeral=True,
            )
            return

        inv = p.setdefault("inventory", {})
        biome = AREA_BIOMES.get(area, {})
        biome_name = biome.get("name", "Unknown Biome")
        biome_drop = biome.get("drop", "crystal shard")

        _, gather_mult = self._get_gear_multipliers(p)
        ore_qty = max(1, int(random.randint(2, 5) * area * gather_mult))
        bonus_qty = max(1, int(random.randint(1, 2) * gather_mult))
        earned_xp = random.randint(14, 28) * area

        inv["iron ore"] = inv.get("iron ore", 0) + ore_qty
        inv[biome_drop] = inv.get(biome_drop, 0) + bonus_qty
        p["xp"] = p.get("xp", 0) + earned_xp

        self._update_quest_progress(p, "mine", ore_qty)
        self._advance_biome_quest(p, "mine", ore_qty)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        crafted_tag = " (✨ Crafted Armor Bonus!)" if p.get("armor_origin") == "crafted" else ""
        await interaction.response.send_message(
            f"⛏️ **Mined in {biome_name}**: +{ore_qty}x Iron Ore | +{bonus_qty}x {biome_drop.title()}{crafted_tag} | +⭐ {earned_xp:,} XP{level_msg}",
            ephemeral=False,
        )

    @gather_group.command(name="wood", description="Chop wood in your current biome.")
    async def gather_wood(self, interaction: discord.Interaction):
        await self.execute_chop(interaction)

    @gather_group.command(name="fish", description="Catch fish in your current biome.")
    async def gather_fish(self, interaction: discord.Interaction):
        await self.execute_fish(interaction)

    @gather_group.command(name="mine", description="Mine iron ore and gems in your current biome (Requires Area 5+).")
    async def gather_mine(self, interaction: discord.Interaction):
        await self.execute_mine(interaction)

    @hardmode_group.command(name="hunt", description="Hunt hardmode monsters in your current biome (Requires Area 13+).")
    async def hardmode_hunt(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        if area < 13:
            await interaction.response.send_message(
                "❌ Hardmode Hunt requires you to be in **Area 13 (Abyssal Depths)** or higher!",
                ephemeral=True,
            )
            return

        biome = AREA_BIOMES.get(area, {})
        biome_drop = biome.get("drop", "common material")

        coin_mult, _ = self._get_gear_multipliers(p)
        sword_bonus = p.get("sword_tier", 1) * 16
        earned_coins = int(((random.randint(45, 95) + sword_bonus) * area) * 1.5 * coin_mult)
        earned_xp = int(random.randint(35, 65) * area * 1.5)
        drop_qty = max(1, int(random.randint(2, 5) * area * 1.5))

        p["wallet"] = p.get("wallet", 0) + earned_coins
        p["xp"] = p.get("xp", 0) + earned_xp
        inv = p.setdefault("inventory", {})
        inv[biome_drop] = inv.get(biome_drop, 0) + drop_qty

        dmg_taken = self._calculate_enemy_damage(p, encounter_type="miniboss")
        max_hp = p.get("max_hp", 100)
        cur_hp = p.get("hp", max_hp)
        if dmg_taken > 0:
            p["hp"] = max(0, cur_hp - dmg_taken)
            hp_msg = f" | 💔 Took **{dmg_taken}** DMG ({p['hp']}/{max_hp} HP)"
        else:
            hp_msg = f" | 🛡️ Dodged! ({cur_hp}/{max_hp} HP)"

        self._update_quest_progress(p, "hunt", 1)
        self._advance_biome_quest(p, "hunt", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        crafted_tag = " (✨ Crafted Bonus!)" if p.get("sword_origin") == "crafted" else ""
        low_hp_tip = "
⚠️ *Low HP! Use `/heal` to patch yourself up.*" if p["hp"] <= max(10, int(p["max_hp"] * 0.25)) else ""
        await interaction.response.send_message(
            f"🔥 **Hardmode Hunt in {biome.get('name', 'Unknown Biome')}**: +🪙 {earned_coins:,}{crafted_tag} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{hp_msg}{level_msg}{low_hp_tip}",
            ephemeral=False,
        )

    @hardmode_group.command(name="adventure", description="Embark on a hardmode adventure in your current biome (Requires Area 14+).")
    async def hardmode_adventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        if area < 14:
            await interaction.response.send_message(
                "❌ Hardmode Adventure requires you to be in **Area 14 (Mythic Overgrowth)** or higher!",
                ephemeral=True,
            )
            return

        biome = AREA_BIOMES.get(area, {})
        biome_drop = biome.get("drop", "common material")

        coin_mult, _ = self._get_gear_multipliers(p)
        sword_bonus = p.get("sword_tier", 1) * 40
        earned_coins = int(((random.randint(160, 340) + sword_bonus) * area) * 1.5 * coin_mult)
        earned_xp = int(random.randint(120, 240) * area * 1.5)
        drop_qty = max(1, int(random.randint(5, 11) * area * 1.5))

        p["wallet"] = p.get("wallet", 0) + earned_coins
        p["xp"] = p.get("xp", 0) + earned_xp
        inv = p.setdefault("inventory", {})
        inv[biome_drop] = inv.get(biome_drop, 0) + drop_qty

        self._update_quest_progress(p, "adventure", 1)
        self._advance_biome_quest(p, "adventure", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        crafted_tag = " (✨ Crafted Bonus!)" if p.get("sword_origin") == "crafted" else ""
        await interaction.response.send_message(
            f"🔥 **Hardmode Adventure in {biome.get('name', 'Unknown Biome')}**: +🪙 {earned_coins:,}{crafted_tag} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{level_msg}",
            ephemeral=False,
        )


async def setup(bot):
    await bot.add_cog(RpgCog(bot))
