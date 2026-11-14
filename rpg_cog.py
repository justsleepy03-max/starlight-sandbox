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
    {"id": "hunt_monsters", "title": "Monster Slayer", "desc": "Hunt 5 times in the wild", "target": 5, "type": "hunt", "reward_coins": 1000, "reward_xp": 500},
    {"id": "gather_wood", "title": "Lumberjack Duty", "desc": "Collect 15 Wood", "target": 15, "type": "chop", "reward_coins": 800, "reward_xp": 400},
    {"id": "catch_fish", "title": "Master Angler", "desc": "Catch 10 Fish", "target": 10, "type": "fish", "reward_coins": 800, "reward_xp": 400},
    {"id": "mine_ore", "title": "Master Miner", "desc": "Mine 10 Iron Ore", "target": 10, "type": "mine", "reward_coins": 1200, "reward_xp": 600},
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
        if str(interaction.user.id) != self
