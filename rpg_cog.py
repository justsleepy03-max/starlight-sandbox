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
    {"id": "hunt_monsters", "title": "Monster Slayer", "desc": "Hunt 5 times in the wild", "target": 5, "type": "hunt", "reward_coins": 1000, "reward_xp": 500, "min_area": 1},
    {"id": "gather_wood", "title": "Lumberjack Duty", "desc": "Collect 15 Wood", "target": 15, "type": "chop", "reward_coins": 800, "reward_xp": 400, "min_area": 1},
    {"id": "catch_fish", "title": "Master Angler", "desc": "Catch 10 Fish", "target": 10, "type": "fish", "reward_coins": 800, "reward_xp": 400, "min_area": 1},
    {"id": "mine_ore", "title": "Master Miner", "desc": "Mine 10 Iron Ore", "target": 10, "type": "mine", "reward_coins": 1200, "reward_xp": 600, "min_area": 5},
    {"id": "forge_gear", "title": "Master Blacksmith", "desc": "Craft or upgrade your gear", "target": 1, "type": "craft", "reward_coins": 2500, "reward_xp": 1000, "min_area": 2},
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
    1: "Default: /hunt, /adventure, /chop, /fish, /shop, /inventory, /quest",
    2: "/enchant, /area, /training",
    3: "/axe, /net, /pickup",
    4: "/ladder, /guild, /farm",
    5: "/mine, /multidice, /cook, /casino",
    6: "/bowsaw, /boat, /pickaxe",
    7: "/refine, /big arena, /alchemy",
    8: "/tractor, /wheel",
    9: "/chainsaw, /bigboat",
    10: "/drill, /minintboss",
    11: "/time travel, /forge, /greenhouse",
    12: "/dynamite, /pets, /petadventure, /ultraining, /badge",
    13: "/transmute, /hunt hardmode",
    14: "/adventure hardmode, /big dice",
    15: "/time jump, /transcend"
}

AREA_LEVEL_REQUIREMENTS = {
    1: 1, 2: 3, 3: 6, 4: 9, 5: 12, 6: 15, 7: 18, 8: 21, 9: 24, 10: 27, 11: 30, 12: 33, 13: 36, 14: 39, 15: 42
}

# --- INTERACTIVE VIEWS ---
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
        embed.add_field(name="Actions & Hub", value="`/profile` - View stats & action hub\n`/hunt` - Hunt monsters in current biome\n`/adventure` - Embark on an epic adventure\n`/chop` - Collect wood\n`/fish` - Catch fish\n`/mine` - Mine iron ore (Area 5+)\n`/heal` - Use potions or life boosts to recover HP", inline=False)
        embed.add_field(name="Progression & Economy", value="`/area` - View or travel between biomes\n`/shop` - Browse interactive shop catalog\n`/buy` - Purchase shop items\n`/inventory` - Check items & materials\n`/bal` - Check wallet & bank\n`/daily` - Claim daily coins\n`/open` - Open loot boxes\n`/craft` - Craft higher gear tiers using materials\n`/quest` / `/claimquest` - Manage quests", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🗺️ Area Expansions", style=discord.ButtonStyle.success, custom_id="help_areas")
    async def areas_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🗺️ Starlight Sandbox - Area Expansions (Areas 2–15)", color=discord.Color.green())
        embed.add_field(name="Early Biomes (Areas 2–6)", value="`/enchant`, `/training`, `/axe`, `/net`, `/pickup`, `/ladder`, `/farm`, `/multidice`, `/cook`, `/casino`, `/bowsaw`, `/boat`, `/pickaxe`", inline=False)
        embed.add_field(name="Mid-High Biomes (Areas 7–12)", value="`/refine`, `/big_arena`, `/alchemy`, `/tractor`, `/wheel`, `/chainsaw`, `/bigboat`, `/drill`, `/minintboss`, `/time_travel`, `/temporal_forge`, `/greenhouse`, `/dynamite`, `/petadventure`, `/ultraining`, `/badge`", inline=False)
        embed.add_field(name="Endgame Biomes (Areas 13–15)", value="`/transmute`, `/hunt_hardmode`, `/adventure_hardmode`, `/big_dice`, `/time_jump`, `/transcend`", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎉 Party Games", style=discord.ButtonStyle.secondary, custom_id="help_party")
    async def party_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎉 Starlight Sandbox - Party Games Suite", color=discord.Color.gold())
        embed.add_field(name="Interactive Games", value="`/cah` - Play Cards Against Humanity with buttons\n`/trivia` - Test knowledge with interactive buttons\n`/connect4` - Play Connect Four board with column buttons\n`/bingo` - Generate a community Bingo card", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)


class RpgCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _update_quest_progress(self, p, action_type, amount=1):
        active = p.get("active_quest")
        if active and active["type"] == action_type and active["progress"] < active["target"]:
            active["progress"] = min(active["target"], active["progress"] + amount)

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
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_drop = biome.get("drop", "common material")
        
        coin_mult, _ = self._get_gear_multipliers(p)
        sword_bonus = p.get("sword_tier", 1) * 8
        earned_coins = int(((random.randint(20, 45) + sword_bonus) * area) * coin_mult)
        earned_xp = random.randint(15, 30) * area
        drop_qty = random.randint(1, 3) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        p["inventory"][biome_drop] = p["inventory"].get(biome_drop, 0) + drop_qty

        dmg_taken = self._calculate_enemy_damage(p, encounter_type="mob")
        max_hp = p.get("max_hp", 100)
        cur_hp = p.get("hp", max_hp)
        if dmg_taken > 0:
            p["hp"] = max(0, cur_hp - dmg_taken)
            hp_msg = f" | 💔 Took **{dmg_taken}** DMG ({p['hp']}/{max_hp} HP)"
        else:
            hp_msg = f" | 🛡️ Dodged! ({cur_hp}/{max_hp} HP)"
        
        self._update_quest_progress(p, "hunt", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        crafted_tag = " (✨ Crafted Bonus!)" if p.get("sword_origin") == "crafted" else ""
        low_hp_tip = "\n⚠️ *Low HP! Use `/heal` to patch yourself up.*" if p["hp"] <= max(10, int(p["max_hp"] * 0.25)) else ""
        await interaction.response.send_message(
            f"⚔️ **Hunt in {biome['name']}**: +🪙 {earned_coins:,}{crafted_tag} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{hp_msg}{level_msg}{low_hp_tip}",
            ephemeral=False
        )

    @discord.app_commands.command(name="adventure", description="Embark on an epic adventure in your current biome.")
    async def adventure(self, interaction: discord.Interaction):
        await self.execute_adventure(interaction)

    async def execute_adventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_drop = biome.get("drop", "common material")
        
        coin_mult, _ = self._get_gear_multipliers(p)
        sword_bonus = p.get("sword_tier", 1) * 20
        earned_coins = int(((random.randint(80, 180) + sword_bonus) * area) * coin_mult)
        earned_xp = random.randint(60, 130) * area
        drop_qty = random.randint(3, 7) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        p["inventory"][biome_drop] = p["inventory"].get(biome_drop, 0) + drop_qty
        
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        await interaction.response.send_message(f"🗺️ **Adventure in {biome['name']}**: +🪙 {earned_coins:,} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{level_msg}", ephemeral=False)

    @discord.app_commands.command(name="chop", description="Collect wood from the local woods.")
    async def chop(self, interaction: discord.Interaction):
        await self.execute_chop(interaction)

    async def execute_chop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        _, gathering_mult = self._get_gear_multipliers(p)
        wood = int(random.randint(2, 6) * p.get("area", 1) * gathering_mult)
        p["inventory"]["wood"] = p["inventory"].get("wood", 0) + wood
        self._update_quest_progress(p, "chop", wood)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        crafted_tag = " (✨ Crafted Armor Bonus!)" if p.get("armor_origin") == "crafted" else ""
        await interaction.response.send_message(f"🪓 You collected **{wood}x Wood**!{crafted_tag}{level_msg}", ephemeral=False)

    @discord.app_commands.command(name="fish", description="Catch fish from the local waters.")
    async def fish(self, interaction: discord.Interaction):
        await self.execute_fish(interaction)

    async def execute_fish(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        fish_caught = random.randint(1, 4) * p.get("area", 1)
        p["inventory"]["fish"] = p["inventory"].get("fish", 0) + fish_caught
        self._update_quest_progress(p, "fish", fish_caught)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"🎣 You caught **{fish_caught}x Fish**!{level_msg}", ephemeral=False)

    @discord.app_commands.command(name="mine", description="Mine iron ore and rare crystals (Requires Area 5+).")
    async def mine(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        if area < 5:
            await interaction.response.send_message("❌ Mining requires you to be in **Area 5 (Crystal Caverns)** or higher!", ephemeral=True)
            return
        
        _, gathering_mult = self._get_gear_multipliers(p)
        ore_mined = int(random.randint(2, 5) * area * gathering_mult)
        p["inventory"]["iron ore"] = p["inventory"].get("iron ore", 0) + ore_mined
        self._update_quest_progress(p, "mine", ore_mined)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        crafted_tag = " (✨ Crafted Armor Bonus!)" if p.get("armor_origin") == "crafted" else ""
        await interaction.response.send_message(f"⛏️ You mined **{ore_mined}x Iron Ore**!{crafted_tag}{level_msg}", ephemeral=False)

    @discord.app_commands.command(name="area", description="View your current area, biomes, unlocks, or travel to a new area.")
    @app_commands.describe(target_area="Area number to travel to")
    async def area(self, interaction: discord.Interaction, target_area: int = None):
        uid = str(interaction.user.id)
        p = get_player(uid)
        current_area = p.get("area", 1)
        unlocked_area = p.get("unlocked_area", 1)

        if target_area is None:
            embed = discord.Embed(title=f"🗺️ Starlight Biome Progression (Current: Area {current_area})", color=discord.Color.blue())
            lines = []
            for a_num, unlocks in AREA_UNLOCKS.items():
                biome_name = AREA_BIOMES.get(a_num, {}).get("name", "Unknown")
                status = '✅ Current' if a_num == current_area else '✅ Unlocked' if a_num <= unlocked_area else '🔒 Locked'
                lines.append(f"**Area {a_num}: {biome_name}** [{status}]\n*🔓 {unlocks}*\n")
            embed.description = "\n".join(lines)
            embed.set_footer(text="Use /area target_area:<num> to travel to your unlocked areas!")
            await interaction.response.send_message(embed=embed)
            return

        if target_area > unlocked_area:
            req_lvl = AREA_LEVEL_REQUIREMENTS.get(target_area, 99)
            await interaction.response.send_message(f"❌ Area {target_area} is locked! Reach **Level {req_lvl}** to automatically unlock it.", ephemeral=True)
            return

        p["area"] = target_area
        update_player(uid, p)
        new_biome = AREA_BIOMES.get(target_area, {}).get("name", "Unknown")
        await interaction.response.send_message(f"🚀 Successfully traveled to **Area {target_area} ({new_biome})**!")

    @discord.app_commands.command(name="inventory", description="Check your items and materials.")
    async def inventory(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        embed.description = "Your inventory is empty!" if not inv else "\n".join([f"• **{item.title()}**: {qty:,}" for item, qty in inv.items()])
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="bal", description="Check your wallet and bank balances.")
    async def bal(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        embed = discord.Embed(title=f"🪙 {interaction.user.display_name}'s Balance", color=discord.Color.gold())
        embed.add_field(name="Bank & Wallet", value=f"🪙 **Wallet:** {p['wallet']:,} coins\n🏛️ **Bank:** {p['bank']:,} coins", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="daily", description="Claim your 24-hour daily reward.")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        now = time.time()
        if now - p.get("last_daily", 0) < 86400:
            await interaction.response.send_message("⏳ You have already claimed your daily reward today!", ephemeral=True)
            return

        bonus = 500 * p.get("area", 1)
        p["wallet"] += bonus
        p["last_daily"] = now
        update_player(uid, p)
        await interaction.response.send_message(f"🎁 Claimed daily reward: 🪙 {bonus:,} coins!")

    @discord.app_commands.command(name="quest", description="Check active quest.")
    async def quest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not p.get("active_quest"):
            player_area = p.get("area", 1)
            available_quests = [q for q in QUEST_POOL if player_area >= q.get("min_area", 1)]
            selected = random.choice(available_quests)
            p["active_quest"] = {
                "id": selected["id"], "title": selected["title"], "desc": selected["desc"],
                "type": selected["type"], "progress": 0, "target": selected["target"],
                "reward_coins": selected["reward_coins"] * player_area, "reward_xp": selected["reward_xp"] * player_area
            }
            update_player(uid, p)
            
        active = p["active_quest"]
        embed = discord.Embed(title="📜 Active Quest", color=discord.Color.gold())
        embed.add_field(name=active["title"], value=f"*{active['desc']}*\n\n**Progress:** {active['progress']}/{active['target']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="claimquest", description="Claim quest rewards.")
    async def claimquest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        active = p.get("active_quest")
        if not active or active["progress"] < active["target"]:
            await interaction.response.send_message("❌ No completed quest to claim!", ephemeral=True)
            return
        p["wallet"] += active["reward_coins"]
        p["xp"] += active["reward_xp"]
        p["active_quest"] = None
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"🎉 Quest Completed! Received 🪙 {active['reward_coins']:,} coins!{level_msg}")

    @discord.app_commands.command(name="abandonquest", description="Abandon your current active quest.")
    async def abandonquest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not p.get("active_quest"):
            await interaction.response.send_message("❌ You don't have an active quest to abandon!", ephemeral=True)
            return
        p["active_quest"] = None
        update_player(uid, p)
        await interaction.response.send_message("🗑️ You have abandoned your active quest. Use `/quest` to pick up a new one!")

    @discord.app_commands.command(name="open", description="Open a loot box from your inventory.")
    @app_commands.describe(box_tier="Choose the tier of loot box to open")
    @app_commands.choices(box_tier=[
        app_commands.Choice(name="Common Lootbox", value="common lootbox"),
        app_commands.Choice(name="Uncommon Lootbox", value="uncommon lootbox"),
        app_commands.Choice(name="Rare Lootbox", value="rare lootbox"),
        app_commands.Choice(name="Epic Lootbox", value="epic lootbox")
    ])
    async def open_box(self, interaction: discord.Interaction, box_tier: str):
        uid = str(
