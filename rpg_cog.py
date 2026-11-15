import os
import json
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, MISC_ITEMS, PET_EGGS, BUNDLES

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

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

# Level requirements required to automatically unlock each area tier
AREA_LEVEL_REQUIREMENTS = {
    1: 1,
    2: 3,
    3: 6,
    4: 9,
    5: 12, # Area 5: Crystal Caverns / Mining Unlock
    6: 15,
    7: 18,
    8: 21,
    9: 24,
    10: 27, # Area 10: Dragon's Spire
    11: 30,
    12: 33,
    13: 36,
    14: 39,
    15: 42
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


class ShopPaginationView(discord.ui.View):
    def __init__(self, cog, user_id, current_page=1):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.current_page = current_page

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ You cannot control someone else's shop menu!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀️ Page 1", style=discord.ButtonStyle.primary, custom_id="shop_p1")
    async def p1_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_shop_embed(1)
        await interaction.response.edit_message(embed=embed, view=ShopPaginationView(self.cog, self.user_id, 1))

    @discord.ui.button(label="Page 2", style=discord.ButtonStyle.primary, custom_id="shop_p2")
    async def p2_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_shop_embed(2)
        await interaction.response.edit_message(embed=embed, view=ShopPaginationView(self.cog, self.user_id, 2))

    @discord.ui.button(label="Page 3 ▶️", style=discord.ButtonStyle.primary, custom_id="shop_p3")
    async def p3_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_shop_embed(3)
        await interaction.response.edit_message(embed=embed, view=ShopPaginationView(self.cog, self.user_id, 3))


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
        embed.add_field(name="Actions & Hub", value="`/profile` - View stats & action hub\n`/hunt` - Hunt monsters in current biome\n`/adventure` - Embark on an epic adventure\n`/chop` - Collect wood\n`/fish` - Catch fish\n`/mine` - Mine iron ore (Area 5+)", inline=False)
        embed.add_field(name="Progression & Economy", value="`/area` - View or travel between biomes\n`/shop` - Browse interactive shop catalog\n`/buy` - Purchase shop items\n`/inventory` - Check items & materials\n`/bal` - Check wallet & bank\n`/daily` - Claim daily coins\n`/open` - Open loot boxes\n`/use` - Use potions & hatch eggs\n`/craft` - Craft gear using biome materials\n`/enchant` - Upgrade gear stats", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🎉 Party Games", style=discord.ButtonStyle.success, custom_id="help_party")
    async def party_help(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎉 Starlight Sandbox - Party Games Suite", color=discord.Color.gold())
        embed.add_field(name="Interactive Games", value="`/cah` - Play Cards Against Humanity with buttons\n`/trivia` - Test knowledge with interactive buttons\n`/connect4` - Play Connect Four board with column buttons\n`/bingo` - Generate a community Bingo card\n`/uno` - Draw starting Uno card\n`/wordchain` - Play Word Chain in chat\n`/truth` or `/dare` - Get random prompts\n`/mafia` - Assign secret roles via DM", inline=False)
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

        # Automatic Area Unlock Check based on Level Thresholds
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

    def get_shop_embed(self, page):
        if page == 1:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 1/3 (Essentials)", color=discord.Color.blue())
            items_text = "🧪 **life potion** | 🪙 25\n🛡️ **basic armor** | 🪙 200\n⚔️ **basic sword** | 🪙 150\n🐎 **basic horse** | 🪙 500\n🔑 **dungeon key** | 🪙 5,000\n🌱 **seed** | 🪙 4,000"
            embed.add_field(name="Catalog", value=items_text, inline=False)
        elif page == 2:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 2/3 (Lootboxes & Eggs)", color=discord.Color.blue())
            items_text = "📦 **common lootbox** | 🪙 800\n📦 **uncommon lootbox** | 🪙 6,000\n📦 **rare lootbox** | 🪙 40,000\n📦 **epic lootbox** | 🪙 150,000\n\n🥚 **common egg** | 🪙 1,000\n🥚 **golden egg** | 🪙 15,000\n🥚 **celestial egg** | 🪙 75,000"
            embed.add_field(name="Catalog", value=items_text, inline=False)
        else:
            embed = discord.Embed(title="✨ Starlight Shop - Page 3/3 (Exclusive Bundles)", color=discord.Color.purple())
            bundles_text = "\n\n".join([f"🎁 **{b_name}** | 🪙 {data['price']}\n*Contents: {', '.join(data['contents'].keys())}*" for b_name, data in BUNDLES.items()])
            embed.add_field(name="Starlight Bundles", value=bundles_text, inline=False)
        return embed

    @discord.app_commands.command(name="help", description="View all available Starlight Sandbox commands and games.")
    async def help(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        embed = discord.Embed(title="🌟 Starlight Sandbox - Help Hub", description="Select a category using the buttons below to explore all RPG commands and Party Games!", color=discord.Color.blurple())
        embed.add_field(name="Quick Overview", value="• **RPG Core**: Level up across 15 biomes, hunt, gather, and quest!\n• **Party Games**: Play Cards Against Humanity, Trivia, Connect Four, Bingo, and more!", inline=False)
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
        
        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile & Action Hub", color=discord.Color.blurple())
        embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']}/{p['level'] * 250} XP)\n**Current Biome:** Area {area} ({biome})\n**Highest Unlocked Area:** Tier {unlocked_area}", inline=False)
        embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
        embed.add_field(name="GEAR", value=f"⚔️ **Sword Tier:** {p.get('sword_tier', 1)}\n🛡️ **Armor Tier:** {p.get('armor_tier', 1)}", inline=False)
        embed.add_field(name="CURRENCY", value=f"🪙 **Wallet:** {p['wallet']:,}\n🏛️ **Bank:** {p['bank']:,}", inline=False)
        embed.set_footer(text="Use the interactive buttons below to play directly from your profile!")

        view = RPGActionView(self, uid)
        await interaction.response.send_message(embed=embed, view=view)

    async def execute_hunt(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_drop = biome.get("drop", "common material")
        
        sword_bonus = p.get("sword_tier", 1) * 5
        earned_coins = (random.randint(20, 45) + sword_bonus) * area
        earned_xp = random.randint(15, 30) * area
        drop_qty = random.randint(1, 3) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        p["inventory"][biome_drop] = p["inventory"].get(biome_drop, 0) + drop_qty
        
        self._update_quest_progress(p, "hunt", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        await interaction.response.send_message(f"⚔️ **Hunt in {biome['name']}**: +🪙 {earned_coins:,} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{level_msg}", ephemeral=False)

    async def execute_adventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        biome_drop = biome.get("drop", "common material")
        
        sword_bonus = p.get("sword_tier", 1) * 15
        earned_coins = (random.randint(80, 180) + sword_bonus) * area
        earned_xp = random.randint(60, 130) * area
        drop_qty = random.randint(3, 7) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        p["inventory"][biome_drop] = p["inventory"].get(biome_drop, 0) + drop_qty
        
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        await interaction.response.send_message(f"🗺️ **Adventure in {biome['name']}**: +🪙 {earned_coins:,} | +⭐ {earned_xp:,} XP | +{drop_qty}x {biome_drop.title()}{level_msg}", ephemeral=False)

    async def execute_chop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        wood = random.randint(2, 6) * p.get("area", 1)
        p["inventory"]["wood"] = p["inventory"].get("wood", 0) + wood
        self._update_quest_progress(p, "chop", wood)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"🪓 You collected **{wood}x Wood**!{level_msg}", ephemeral=False)

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
        
        ore_mined = random.randint(2, 5) * area
        p["inventory"]["iron ore"] = p["inventory"].get("iron ore", 0) + ore_mined
        self._update_quest_progress(p, "mine", ore_mined)
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"⛏️ You mined **{ore_mined}x Iron Ore**!{level_msg}", ephemeral=False)

    @discord.app_commands.command(name="area", description="View your current area, biomes, unlocks, or travel to a new area.")
    @discord.app_commands.describe(target_area="Area number to travel to")
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

        if target_area > 15 or target_area < 1:
            await interaction.response.send_message("❌ Areas range from 1 to 15.", ephemeral=True)
            return

        p["area"] = target_area
        update_player(uid, p)
        new_biome = AREA_BIOMES.get(target_area, {}).get("name", "Unknown")
        await interaction.response.send_message(f"🚀 Successfully traveled to **Area {target_area} ({new_biome})**!")

    @discord.app_commands.command(name="shop", description="View the Starlight Shop catalog with interactive page buttons.")
    async def shop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        embed = self.get_shop_embed(1)
        view = ShopPaginationView(self, uid, 1)
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="buy", description="Buy an item from the Starlight Shop catalog.")
    @app_commands.describe(item_name="Name of the item to buy", quantity="Quantity to purchase (default 1)")
    async def buy(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        item_lower = item_name.lower().strip()
        
        SHOP_PRICES = {
            "life potion": 25,
            "basic armor": 200,
            "basic sword": 150,
            "basic horse": 500,
            "dungeon key": 5000,
            "seed": 4000,
            "common lootbox": 800,
            "uncommon lootbox": 6000,
            "rare lootbox": 40000,
            "epic lootbox": 150000,
            "common egg": 1000,
            "golden egg": 15000,
            "celestial egg": 75000
        }
        
        if item_lower not in SHOP_PRICES:
            await interaction.response.send_message(f"❌ Unknown item **'{item_name}'**! Check `/shop` for valid catalog items.", ephemeral=True)
            return
            
        if quantity < 1:
            await interaction.response.send_message("❌ You must buy at least 1 of an item.", ephemeral=True)
            return
            
        total_cost = SHOP_PRICES[item_lower] * quantity
        
        if p["wallet"] < total_cost:
            await interaction.response.send_message(f"❌ You don't have enough coins! You need **🪙 {total_cost:,}** coins, but your wallet has **🪙 {p['wallet']:,}**.", ephemeral=True)
            return
            
        p["wallet"] -= total_cost
        inv = p.setdefault("inventory", {})
        inv[item_lower] = inv.get(item_lower, 0) + quantity
        
        update_player(uid, p)
        
        await interaction.response.send_message(f"🛒 Successfully purchased **{quantity}x {item_name.title()}** for **🪙 {total_cost:,} coins**!")

    @discord.app_commands.command(name="inventory", description="Check your items and materials.")
    async def inventory(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        if not inv:
            embed.description = "Your inventory is empty!"
        else:
            embed.description = "\n".join([f"• **{item.title()}**: {qty}" for item, qty in inv.items()])
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
        last_claimed = p.get("last_daily", 0)
        cooldown_period = 24 * 60 * 60  # 24 hours in seconds
        
        if now - last_claimed < cooldown_period:
            remaining = int(cooldown_period - (now - last_claimed))
            hours, remainder = divmod(remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            await interaction.response.send_message(f"⏳ You have already claimed your daily reward! Come back in **{hours}h {minutes}m {seconds}s**.", ephemeral=True)
            return

        bonus = 500 * p.get("area", 1)
        p["wallet"] += bonus
        p["last_daily"] = now
        update_player(uid, p)
        await interaction.response.send_message(f"🎁 Claimed daily reward: 🪙 {bonus:,} coins!")

    @discord.app_commands.command(name="heal", description="Restore HP.")
    async def heal(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        p["hp"] = p["max_hp"]
        update_player(uid, p)
        await interaction.response.send_message(f"❤️ Restored HP to {p['max_hp']}!")

    @discord.app_commands.command(name="quest", description="Check active quest.")
    async def quest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if "active_quest" not in p:
            p["active_quest"] = None
        active = p["active_quest"]
        
        if not active:
            player_area = p.get("area", 1)
            # Filter pool based on player's current area
            available_quests = [q for q in QUEST_POOL if player_area >= q.get("min_area", 1)]
            
            if not available_quests:
                available_quests = [QUEST_POOL[0]] # Fallback
                
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

    @discord.app_commands.command(name="abandonquest", description="Abandon your current active quest to take on a new one.")
    async def abandonquest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        if not p.get("active_quest"):
            await interaction.response.send_message("❌ You don't have an active quest to abandon!", ephemeral=True)
            return
            
        p["active_quest"] = None
        update_player(uid, p)
        await interaction.response.send_message("🗑️ You have abandoned your active quest. Use `/quest` to pick up a new one matching your current area!")

    # --- LOOT BOX OPENING SYSTEM ---
    @discord.app_commands.command(name="open", description="Open a loot box from your inventory.")
    @app_commands.describe(box_tier="Choose the tier of loot box to open")
    @app_commands.choices(box_tier=[
        app_commands.Choice(name="Common Lootbox", value="common lootbox"),
        app_commands.Choice(name="Uncommon Lootbox", value="uncommon lootbox"),
        app_commands.Choice(name="Rare Lootbox", value="rare lootbox"),
        app_commands.Choice(name="Epic Lootbox", value="epic lootbox")
    ])
    async def open_box(self, interaction: discord.Interaction, box_tier: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})

        if inv.get(box_tier, 0) < 1:
            await interaction.response.send_message(f"❌ You don't have a **{box_tier.title()}** in your inventory! Buy one from `/shop`.", ephemeral=True)
            return

        inv[box_tier] -= 1
        if inv[box_tier] <= 0:
            del inv[box_tier]

        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {})
        drop_item = biome.get("drop", "soft bark")

        rewards_text = []
        
        if box_tier == "common lootbox":
            coins = random.randint(200, 500) * area
            mat_qty = random.randint(3, 8)
            p["wallet"] += coins
            inv[drop_item] = inv.get(drop_item, 0) + mat_qty
            rewards_text.append(f"🪙 +{coins:,} Coins")
            rewards_text.append(f"📦 +{mat_qty}x {drop_item.title()}")
            
            if random.random() < 0.10:
                inv["common egg"] = inv.get("common egg", 0) + 1
                rewards_text.append("🥚 **Common Egg!**")

        elif box_tier == "uncommon lootbox":
            coins = random.randint(1000, 2500) * area
            mat_qty = random.randint(8, 15)
            p["wallet"] += coins
            inv[drop_item] = inv.get(drop_item, 0) + mat_qty
            rewards_text.append(f"🪙 +{coins:,} Coins")
            rewards_text.append(f"📦 +{mat_qty}x {drop_item.title()}")
            
            roll = random.random()
            if roll < 0.05:
                inv["golden egg"] = inv.get("golden egg", 0) + 1
                rewards_text.append("🥚✨ **Golden Egg!**")
            elif roll < 0.20:
                inv["common egg"] = inv.get("common egg", 0) + 1
                rewards_text.append("🥚 **Common Egg!**")

        elif box_tier == "rare lootbox":
            coins = random.randint(8000, 18000) * area
            mat_qty = random.randint(15, 30)
            p["wallet"] += coins
            inv[drop_item] = inv.get(drop_item, 0) + mat_qty
            rewards_text.append(f"🪙 +{coins:,} Coins")
            rewards_text.append(f"📦 +{mat_qty}x {drop_item.title()}")
            
            roll = random.random()
            if roll < 0.05:
                inv["celestial egg"] = inv.get("celestial egg", 0) + 1
                rewards_text.append("🌟🥚 **Celestial Egg!**")
            elif roll < 0.25:
                inv["golden egg"] = inv.get("golden egg", 0) + 1
                rewards_text.append("🥚✨ **Golden Egg!**")

        elif box_tier == "epic lootbox":
            coins = random.randint(40000, 90000) * area
            mat_qty = random.randint(30, 60)
            p["wallet"] += coins
            inv[drop_item] = inv.get(drop_item, 0) + mat_qty
            rewards_text.append(f"🪙 +{coins:,} Coins")
            rewards_text.append(f"📦 +{mat_qty}x {drop_item.title()}")
            
            roll = random.random()
            if roll < 0.15:
                inv["celestial egg"] = inv.get("celestial egg", 0) + 1
                rewards_text.append("🌟🥚 **Celestial Egg!**")
            elif roll < 0.50:
                inv["golden egg"] = inv.get("golden egg", 0) + 1
                rewards_text.append("🥚✨ **Golden Egg!**")

        update_player(uid, p)
        
        embed = discord.Embed(title=f"📦 Opened {box_tier.title()}", description=f"You opened a loot box and obtained:\n\n" + "\n".join([f"• {r}" for r in rewards_text]), color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)

    # --- USE ITEM SYSTEM (Potions, Eggs) ---
    @discord.app_commands.command(name="use", description="Use an item from your inventory (e.g. life potions, pet eggs).")
    @app_commands.describe(item_name="Name of the item to use")
    async def use_item(self, interaction: discord.Interaction, item_name: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        
        item_lower = item_name.lower().strip()
        
        if inv.get(item_lower, 0) < 1:
            await interaction.response.send_message(f"❌ You don't have any **{item_name.title()}** in your inventory!", ephemeral=True)
            return

        if item_lower == "life potion":
            if p["hp"] >= p["max_hp"]:
                await interaction.response.send_message("❤️ Your HP is already completely full!", ephemeral=True)
                return
                
            inv[item_lower] -= 1
            if inv[item_lower] <= 0:
                del inv[item_lower]
                
            p["hp"] = p["max_hp"]
            update_player(uid, p)
            await interaction.response.send_message(f"🧪 You drank a Life Potion and fully restored your HP to **{p['max_hp']}**!")
            return

        elif item_lower in ["common egg", "golden egg", "celestial egg"]:
            inv[item_lower] -= 1
            if inv[item_lower] <= 0:
                del inv[item_lower]
                
            if item_lower == "common egg":
                pet_name = random.choice(["Shadow Mouse", "Forest Sprite", "Pebble Pup"])
            elif item_lower == "golden egg":
                pet_name = random.choice(["Golden Phoenix", "Sun Cub", "Crystal Drake"])
            else:
                pet_name = "Starlight Celestial Spirit"
                
            update_player(uid, p)
            await interaction.response.send_message(f"🥚✨ You cracked open your **{item_name.title()}** and successfully hatched a new pet: **{pet_name}**!")
            return

        else:
            await interaction.response.send_message(f"❌ You cannot 'use' a **{item_name.title()}** directly. (If it's a loot box, use `/open` instead!)", ephemeral=True)

    # --- CRAFTING, EQUIPPING & ENCHANTING ---
    @discord.app_commands.command(name="craft", description="Craft upgraded swords or armor using biome materials.")
    @app_commands.describe(gear_type="Choose weapon or armor", tier="Target tier to craft")
    @app_commands.choices(gear_type=[
        app_commands.Choice(name="Sword", value="sword"),
        app_commands.Choice(name="Armor", value="armor")
    ])
    async def craft(self, interaction: discord.Interaction, gear_type: str, tier: int):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})

        if tier < 2 or tier > 5:
            await interaction.response.send_message("❌ Craftable gear tiers range from Tier 2 to Tier 5.", ephemeral=True)
            return

        current_tier = p.get(f"{gear_type}_tier", 1)
        if tier <= current_tier:
            await interaction.response.send_message(f"❌ You already own or exceed Tier {tier} {gear_type}!", ephemeral=True)
            return

        if tier > current_tier + 1:
            await interaction.response.send_message(f"❌ You must craft Tier {current_tier + 1} first before jumping to Tier {tier}!", ephemeral=True)
            return

        cost = tier * 10
        material = AREA_BIOMES.get(tier, {}).get("drop", "soft bark")
        
        if inv.get(material, 0) < cost:
            await interaction.response.send_message(f"❌ You need **{cost}x {material.title()}** to craft this tier!", ephemeral=True)
            return

        inv[material] -= cost
        p[f"{gear_type}_tier"] = tier
        update_player(uid, p)
        await interaction.response.send_message(f"⚒️ Successfully crafted **Tier {tier} {gear_type.title()}** using {cost}x {material.title()}!")

    @discord.app_commands.command(name="enchant", description="Enchant your gear using magic essences.")
    async def enchant(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        if area < 2:
            await interaction.response.send_message("❌ Enchanting unlocks at **Area 2**!", ephemeral=True)
            return
        
        p["max_hp"] += 10
        p["hp"] = p["max_hp"]
        update_player(uid, p)
        await interaction.response.send_message(f"✨ Enchanted successfully! Max HP permanently increased to **{p['max_hp']}**.")

async def setup(bot):
    await bot.add_cog(RpgCog(bot))
