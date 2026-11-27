import os
import json
import random
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

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
        potions = player_data.get("inventory", {}).get("life potion", 0)
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

    def _calculate_player_damage(self, player_data: dict) -> tuple[int, bool]:
        level = player_data.get("level", 1)
        sword_tier = player_data.get("sword_tier", 1)
        pet_mult = get_pet_combat_bonus(self.user_id)

        base_dmg = (18 + (level * 4) + (sword_tier * 22)) * pet_mult
        is_crit = random.random() < 0.20
        dmg = int(base_dmg * random.uniform(0.85, 1.15) * (1.6 if is_crit else 1.0))
        return max(5, dmg), is_crit

    def _calculate_enemy_damage(self, player_data: dict, guarding: bool = False) -> int:
        armor_tier = player_data.get("armor_tier", 1)
        reduction = min(0.60, armor_tier * 0.05)  # Up to 60% reduction at Tier 12 armor
        raw_dmg = self.enemy_atk * random.uniform(0.80, 1.20)
        final_dmg = raw_dmg * (1.0 - reduction)
        if guarding:
            final_dmg *= 0.35
        return max(1, int(final_dmg))

    async def _handle_victory(self, interaction: discord.Interaction, player_data: dict):
        mults = get_ng_multipliers(self.ng_tier)
        current_cleared = get_tier_cleared_floor(player_data, self.ng_tier)
        is_first_clear = self.floor > current_cleared

        # Rebalanced base rewards + NG+ scaling + 60% repeat-clear multiplier to prevent floor farming inflation
        base_coins = (45 * self.floor) + (600 if self.is_boss else 0)
        base_xp = (35 * self.floor) + (400 if self.is_boss else 0)
        farm_mult = 1.0 if is_first_clear else 0.60

        coins_won = max(15, int(base_coins * mults["reward"] * farm_mult))
        xp_won = max(10, int(base_xp * mults["reward"] * farm_mult))

        player_data["wallet"] = player_data.get("wallet", 0) + coins_won
        player_data["xp"] = player_data.get("xp", 0) + xp_won
        player_data.setdefault("level", 1)
        player_data.setdefault("max_hp", 100)
        player_data.setdefault("hp", player_data["max_hp"])

        if is_first_clear:
            set_tier_cleared_floor(player_data, self.ng_tier, self.floor)

        if self.floor <= 25:
            pool = LOOT_TABLES["tier_1"]
        elif self.floor <= 50:
            pool = LOOT_TABLES["tier_2"]
        elif self.floor <= 75:
            pool = LOOT_TABLES["tier_3"]
        else:
            pool = LOOT_TABLES["tier_4"]

        inv = player_data.setdefault("inventory", {})
        loot_summary = []

        drop_1 = random.choice(pool)
        qty_1 = random.randint(2, 3) if self.is_boss else 1
        inv[drop_1] = inv.get(drop_1, 0) + qty_1
        loot_summary.append(f"**{qty_1}x {drop_1.title()}**")

        if self.is_boss:
            bonus_drop = random.choice(LOOT_TABLES["tier_3"] if self.floor < 60 else LOOT_TABLES["tier_4"])
            inv[bonus_drop] = inv.get(bonus_drop, 0) + 1
            loot_summary.append(f"**1x {bonus_drop.title()}**")

            boss_info = BOSS_FLOORS.get(self.floor, {})
            trophy_item = boss_info.get("trophy")
            if trophy_item and inv.get(trophy_item, 0) == 0:
                inv[trophy_item] = 1
                loot_summary.append(f"✨ **1x {trophy_item.title()} (Legendary Trophy)**")

        # Handle Floor 100 NG+ unlock progression
        ng_unlock_msg = ""
        if self.floor == 100:
            ng_unlocked = int(player_data.get("spire_ng_unlocked", 0))
            if self.ng_tier >= ng_unlocked:
                next_ng = self.ng_tier + 1
                player_data["spire_ng_unlocked"] = next_ng
                ng_unlock_msg = f"\n🔥 **NEW GAME+ UNLOCKED!** You can now challenge **NG+{next_ng}** using `/ngplus`!"

        xp_needed = player_data["level"] * 250
        lvl_up_text = ""
        while player_data["xp"] >= xp_needed:
            player_data["xp"] -= xp_needed
            player_data["level"] += 1
            player_data["max_hp"] += 20
            player_data["hp"] = player_data["max_hp"]
            lvl_up_text = f"\n🎉 **LEVEL UP!** You reached **Level {player_data['level']}**!"
            xp_needed = player_data["level"] * 250

        update_player(self.user_id, player_data)

        tier_label = format_ng_label(self.ng_tier)
        if self.floor == 100:
            next_floor_msg = f"🏆 **CONGRATULATIONS! YOU CONQUERED FLOOR 100 ({tier_label}) OF THE STARLIGHT SPIRE!**{ng_unlock_msg}"
        elif is_first_clear:
            next_floor_msg = f"🔓 **Floor {self.floor + 1} ({tier_label})** is now unlocked!"
        else:
            next_floor_msg = f"♻️ *Replay clear ({tier_label}) — 60% coin/XP yield applied.*"

        self.combat_log.append(f"🏆 Defeated **{self.enemy_name}**!")
        embed = self.build_combat_embed(player_data, status_color=discord.Color.green())
        embed.add_field(
            name="🎁 Floor Clear Rewards",
            value=f"🪙 **+{coins_won:,} coins** | ⭐ **+{xp_won:,} XP**\n📦 **Loot:** {', '.join(loot_summary)}\n{next_floor_msg}{lvl_up_text}",
            inline=False
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def _handle_defeat(self, interaction: discord.Interaction, player_data: dict):
        player_data["hp"] = max(25, int(player_data.get("max_hp", 100) * 0.25))
        update_player(self.user_id, player_data)

        self.combat_log.append(f"💀 You were defeated by **{self.enemy_name}** and warped out of the spire!")
        embed = self.build_combat_embed(player_data, status_color=discord.Color.dark_red())
        embed.add_field(
            name="💫 Emergency Warp",
            value="You were teleported back to safety with 25% HP. Upgrade your gear with `/craft` or stock up on Life Potions in `/shop`!",
            inline=False
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="⚔️ Strike", style=discord.ButtonStyle.danger)
    async def strike_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_data = get_player(self.user_id)
        player_data.setdefault("max_hp", 100)
        player_data.setdefault("hp", player_data["max_hp"])

        dmg, is_crit = self._calculate_player_damage(player_data)
        self.enemy_hp -= dmg

        crit_tag = " 💥 **CRIT!**" if is_crit else ""
        self.combat_log.append(f"⚔️ You struck **{self.enemy_name}** for **{dmg:,}** damage!{crit_tag}")

        if self.enemy_hp <= 0:
            return await self._handle_victory(interaction, player_data)

        enemy_dmg = self._calculate_enemy_damage(player_data, guarding=False)
        player_data["hp"] -= enemy_dmg
        self.combat_log.append(f"👹 **{self.enemy_name}** counter-attacked for **{enemy_dmg:,}** damage!")

        if player_data["hp"] <= 0:
            return await self._handle_defeat(interaction, player_data)

        update_player(self.user_id, player_data)
        await interaction.response.edit_message(embed=self.build_combat_embed(player_data), view=self)

    @discord.ui.button(label="🛡️ Guard", style=discord.ButtonStyle.primary)
    async def guard_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_data = get_player(self.user_id)
        max_hp = player_data.get("max_hp", 100)
        cur_hp = player_data.get("hp", max_hp)

        enemy_dmg = self._calculate_enemy_damage(player_data, guarding=True)
        heal_amt = max(5, int(max_hp * 0.08))

        player_data["max_hp"] = max_hp
        player_data["hp"] = min(max_hp, cur_hp - enemy_dmg + heal_amt)
        self.combat_log.append(f"🛡️ You raised your guard! Took **{enemy_dmg:,}** reduced damage and recovered **{heal_amt}** HP.")

        if player_data["hp"] <= 0:
            return await self._handle_defeat(interaction, player_data)

        update_player(self.user_id, player_data)
        await interaction.response.edit_message(embed=self.build_combat_embed(player_data), view=self)

    @discord.ui.button(label="🧪 Life Potion", style=discord.ButtonStyle.success)
    async def potion_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_data = get_player(self.user_id)
        inv = player_data.setdefault("inventory", {})

        if inv.get("life potion", 0) < 1:
            return await interaction.response.send_message("❌ You don't have any **Life Potions** in your bag! Buy some in `/shop`.", ephemeral=True)

        inv["life potion"] -= 1
        if inv["life potion"] <= 0:
            del inv["life potion"]

        max_hp = player_data.get("max_hp", 100)
        cur_hp = player_data.get("hp", max_hp)
        heal_amt = max(35, int(max_hp * 0.50))
        player_data["hp"] = min(max_hp, cur_hp + heal_amt)
        update_player(self.user_id, player_data)

        self.combat_log.append(f"🧪 You drank a **Life Potion** and restored **{heal_amt:,} HP**!")
        await interaction.response.edit_message(embed=self.build_combat_embed(player_data), view=self)

    @discord.ui.button(label="🏃 Retreat", style=discord.ButtonStyle.secondary)
    async def retreat_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"🏃 Retreated from Floor {self.floor} ({format_ng_label(self.ng_tier)})",
            description="You safely used a Teleport Crystal to exit the Starlight Spire.",
            color=discord.Color.light_grey()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class DungeonsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="dungeon", description="Challenge the 100-Floor Starlight Spire (SAO-style tower climb).")
    @app_commands.describe(floor="Optional floor number to challenge (defaults to your next uncleared floor)")
    async def dungeon(self, interaction: discord.Interaction, floor: int = None):
        uid = str(interaction.user.id)
        player_data = get_player(uid)

        ng_unlocked = int(player_data.get("spire_ng_unlocked", 0))
        ng_tier = min(int(player_data.get("spire_ng_current", 0)), ng_unlocked)
        player_data["spire_ng_current"] = ng_tier

        highest_cleared = get_tier_cleared_floor(player_data, ng_tier)
        max_accessible = min(100, highest_cleared + 1)
        target_floor = floor if floor is not None else max_accessible

        if target_floor < 1 or target_floor > 100:
            return await interaction.response.send_message("❌ The Starlight Spire has **100 Floors** (1 to 100)!", ephemeral=True)

        if target_floor > max_accessible:
            return await interaction.response.send_message(
                f"❌ Floor **{target_floor}** ({format_ng_label(ng_tier)}) is locked! You must clear **Floor {max_accessible}** first.",
                ephemeral=True
            )

        if player_data.get("hp", 100) <= 15:
            return await interaction.response.send_message(
                "❌ Your HP is too low to enter the dungeon! Use a **Life Potion** or level up first.",
                ephemeral=True
            )

        is_boss = (target_floor % 10 == 0)

        if is_boss:
            inv = player_data.setdefault("inventory", {})
            if inv.get("dungeon key", 0) < 1:
                return await interaction.response.send_message(
                    f"🔑 **Floor {target_floor}** is a **Boss Room** and requires **1x Dungeon Key**! Buy one in `/shop` or earn them from quests.",
                    ephemeral=True
                )
            inv["dungeon key"] -= 1
            if inv["dungeon key"] <= 0:
                del inv["dungeon key"]
            update_player(uid, player_data)

        mults = get_ng_multipliers(ng_tier)

        if is_boss:
            boss_info = BOSS_FLOORS.get(target_floor, {"name": f"Floor {target_floor} Overlord", "title": "Boss"})
            enemy_name = f"{boss_info['name']} ({boss_info['title']})"
            base_hp = 150 + (target_floor * 45)
            base_atk = 14 + int(target_floor * 2.4)
        else:
            guardian = FLOOR_GUARDIANS[(target_floor - 1) % len(FLOOR_GUARDIANS)]
            enemy_name = f"Floor {target_floor} {guardian}"
            base_hp = 70 + (target_floor * 24)
            base_atk = 8 + int(target_floor * 1.6)

        enemy_hp = int(base_hp * mults["hp"])
        enemy_atk = int(base_atk * mults["atk"])

        view = DungeonCombatView(
            user_id=uid,
            floor=target_floor,
            ng_tier=ng_tier,
            enemy_name=enemy_name,
            enemy_hp=enemy_hp,
            enemy_max_hp=enemy_hp,
            enemy_atk=enemy_atk,
            is_boss=is_boss
        )
        embed = view.build_combat_embed(player_data)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="ngplus", description="View or switch your Starlight Spire New Game+ (NG+) difficulty tier.")
    @app_commands.describe(tier="NG+ tier to switch to (0 = Normal, 1 = NG+1, 2 = NG+2, etc.)")
    async def ngplus(self, interaction: discord.Interaction, tier: int = None):
        uid = str(interaction.user.id)
        player_data = get_player(uid)

        normal_cleared = int(player_data.get("dungeon_floor", 0))
        ng_unlocked = int(player_data.get("spire_ng_unlocked", 0))
        ng_current = int(player_data.get("spire_ng_current", 0))

        # Safety check: if normal Floor 100 was already cleared before this update, grant NG+1
        if normal_cleared >= 100 and ng_unlocked == 0:
            ng_unlocked = 1
            player_data["spire_ng_unlocked"] = 1
            update_player(uid, player_data)

        if tier is not None:
            if tier < 0:
                return await interaction.response.send_message("❌ NG+ tier cannot be negative! Use `0` for Normal or `1+` for NG+.", ephemeral=True)
            if tier > ng_unlocked:
                req_tier = "Normal" if tier == 1 else f"NG+{tier - 1}"
                return await interaction.response.send_message(
                    f"🔒 **NG+{tier}** is locked! Defeat **Floor 100** on **{req_tier}** to unlock it.",
                    ephemeral=True
                )
            player_data["spire_ng_current"] = tier
            update_player(uid, player_data)
            ng_current = tier

        active_mults = get_ng_multipliers(ng_current)
        tier_floor = get_tier_cleared_floor(player_data, ng_current)

        embed = discord.Embed(
            title="🔥 Starlight Spire — New Game+ (NG+)",
            description=(
                f"**Active Difficulty:** {format_ng_label(ng_current)} (Floor {tier_floor} / 100 cleared)\n"
                f"**Highest Unlocked Tier:** {format_ng_label(ng_unlocked)}\n\n"
                f"**Current Multipliers:**\n"
                f"💥 Enemy ATK: **{active_mults['atk']}x** | ❤️ Enemy HP: **{active_mults['hp']}x** | 🪙 Rewards: **{active_mults['reward']}x**"
            ),
            color=discord.Color.gold()
        )

        tier_lines = []
        max_preview = max(5, ng_unlocked + 1)
        for t in range(0, max_preview + 1):
            m = get_ng_multipliers(t)
            t_cleared = get_tier_cleared_floor(player_data, t)
            if t == ng_current:
                state = f"▶️ Active ({t_cleared}/100)"
            elif t <= ng_unlocked:
                state = f"✅ Unlocked ({t_cleared}/100)"
            else:
                state = "🔒 Locked"
            tier_lines.append(
                f"**{format_ng_label(t)}** — ATK `{m['atk']}x` | HP `{m['hp']}x` | Loot `{m['reward']}x` [{state}]"
            )

        embed.add_field(name="📊 NG+ Difficulty Tiers", value="\n".join(tier_lines), inline=False)
        embed.set_footer(text="Defeat Floor 100 to unlock the next tier • Switch anytime with /ngplus <tier>")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="tower", description="Check your 100-Floor Starlight Spire progress and upcoming Boss Floors.")
    async def tower(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        player_data = get_player(uid)

        ng_unlocked = int(player_data.get("spire_ng_unlocked", 0))
        ng_current = min(int(player_data.get("spire_ng_current", 0)), ng_unlocked)
        cleared = get_tier_cleared_floor(player_data, ng_current)
        next_floor = min(100, cleared + 1)

        embed = discord.Embed(
            title=f"🏰 Starlight Spire — 100-Floor Progress ({format_ng_label(ng_current)})",
            description=(
                f"**Active Mode:** {format_ng_label(ng_current)} (Unlocked up to {format_ng_label(ng_unlocked)})\n"
                f"**Highest Cleared Floor:** Floor {cleared} / 100\n"
                f"**Next Floor to Challenge:** Floor {next_floor}\n\n"
                f"*Every 10th floor is a Boss Room requiring 1x Dungeon Key. Switch tiers via `/ngplus`.*"
            ),
            color=discord.Color.purple()
        )

        boss_lines = []
        for f_num, b_data in BOSS_FLOORS.items():
            status = "✅ Cleared" if cleared >= f_num else ("⚔️ Next Boss" if f_num - cleared <= 10 else "🔒 Locked")
            boss_lines.append(f"**Floor {f_num}:** {b_data['name']} [{status}]")

        embed.add_field(name="👑 Spire Floor Bosses", value="\n".join(boss_lines), inline=False)
        embed.set_footer(text="Use /dungeon to climb the tower • Use /ngplus to manage NG+ tiers!")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(DungeonsCog(bot))
