import os
import json
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player
from items import ARMORS

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
class RPGActionView(discord.ui.View):
    def __init__(self, cog, user_id):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This action menu doesn't belong to you! Use `/profile` to open your own.", ephemeral=True)
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


class EconomyAmountModal(discord.ui.Modal):
    def __init__(self, cog, user_id: str, action: str, source_view: "EconomyView"):
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
                "`/area` - View biomes/unlocks or travel to an unlocked area\n"
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
            messages.append(f"\n🎉 **LEVEL UP!** You reached **Level {p['level']}**! Max HP increased to {p['max_hp']}.")
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
            messages.append(f"\n🚀 **AREA UNLOCKED!** Your level progression automatically unlocked **Area {highest_eligible} ({new_biome_name})**!")

        return "".join(messages)

    def _get_gear_multipliers(self, p):
        sword_origin = p.get("sword_origin", "shop")
        armor_origin = p.get("armor_origin", "shop")
        
        coin_mult = 1.15 if sword_origin == "crafted" else 1.0     # Crafted swords give +15% hunt coins
        gathering_mult = 1.25 if armor_origin == "crafted" else 1.0 # Crafted armor gives +25% gathering yield
        
        return coin_mult, gathering_mult

    def _calculate_enemy_damage(self, p, encounter_type="mob"):
        """50% chance to deal damage; scales with area and reduces via equipped armor defense."""
        if random.random() >= 0.50:
            return 0  # 50% chance the enemy misses / player evades

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
            value=f"🪙 **Wallet:** {wallet:,} coins\n🏛️ **Bank:** {bank:,} coins\n💎 **Total:** {wallet + bank:,} coins",
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
        description="Owner only: Give a custom beta tester bundle with coins and items."
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
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Starlight Community Bot • Button Navigation")
        view = HelpView(self, uid)
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="profile", description="Check your RPG character stats, gear, and action buttons.")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        unlocked_area = p.get("unlocked_area", area)
        biome = AREA_BIOMES.get(area, {}).get("name", "Unknown Biome")
        
        s_origin = f"({p.get('sword_origin', 'shop').upper()})"
        a_origin = f"({p.get('armor_origin', 'shop').upper()})"
        
        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile & Action Hub", color=discord.Color.blurple())
        embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']}/{p['level'] * 250} XP)\n**Current Biome:** Area {area} ({biome})\n**Highest Unlocked Area:** Tier {unlocked_area}", inline=False)
        embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
        embed.add_field(name="GEAR", value=f"⚔️ **Sword Tier:** {p.get('sword_tier', 1)} {s_origin}\n🛡️ **Armor Tier:** {p.get('armor_tier', 1)} {a_origin}", inline=False)
        embed.add_field(name="CURRENCY", value=f"🪙 **Wallet:** {p['wallet']:,}\n🏛️ **Bank:** {p['bank']:,}", inline=False)
        embed.set_footer(text="Use the interactive buttons below to play directly from your profile!")

        view = RPGActionView(self, uid)
        await interaction.response.send_message(embed=embed, view=view)

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
                    ephemeral=True
                )
                return
        else:
            chosen = next((k for k in HEALING_PRIORITY if inv.get(k, 0) > 0), None)
            if not chosen:
                await interaction.response.send_message(
                    "❌ You don't have any healing bottles or elixirs in your inventory! Grab some from `/shop`.",
                    ephemeral=True
                )
                return

        owned = inv.get(chosen, 0)
        if owned < quantity:
            await interaction.response.send_message(
                f"❌ You only have **{owned}x {chosen.title()}** in your inventory!",
                ephemeral=True
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
        low_hp_tip = "\n⚠️ *Low HP! Use `/heal` to patch yourself up.*" if p["hp"] <= max(10, int(p["max_hp"] * 0.25)) else ""
        await interaction.response.send_message(
            f"⚔️ **Hunt in {biome_name}**: +🪙 {earned_coins:,}{crafted_tag} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{hp_msg}{level_msg}{low_hp_tip}",
            ephemeral=False
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
        
        await interaction.response.send_message(f"🗺️ **Adventure in {biome_name}**: +🪙 {earned_coins:,} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{level_msg}", ephemeral=False)

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
        low_hp_tip = "\n⚠️ *Low HP! Use `/heal` to patch yourself up.*" if p["hp"] <= max(10, int(p["max_hp"] * 0.25)) else ""
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
