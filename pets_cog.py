import os
import json
import random
import discord
from discord import app_commands
from discord.ext import commands

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

def load_pets_data():
    if not os.path.exists(PETS_FILE):
        return {}
    try:
        with open(PETS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_pets_data(data):
    with open(PETS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Pet Roster Definitions
PET_DATABASE = {
    "Starlight Slime": {"rarity": "Common", "type": "Common Egg", "buff_desc": "+2% Coin bonus on commands", "buff_type": "coin", "value": 0.02},
    "Pebble Crab": {"rarity": "Common", "type": "Common Egg", "buff_desc": "+1 Defense in quests", "buff_type": "defense", "value": 1},
    "Shadow Mouse": {"rarity": "Common", "type": "Common Egg", "buff_desc": "Slightly reduced command cooldowns (-1%)", "buff_type": "cooldown", "value": 0.01},
    
    "Sunwing Finch": {"rarity": "Uncommon", "type": "Golden Egg", "buff_desc": "+5% Expedition speed", "buff_type": "expedition", "value": 0.05},
    "Crystal Hedgehog": {"rarity": "Uncommon", "type": "Golden Egg", "buff_desc": "+5% chance to find bonus crafting materials", "buff_type": "materials", "value": 0.05},
    "Ember Fox": {"rarity": "Rare", "type": "Golden Egg", "buff_desc": "+10% Attack power during RPG battles", "buff_type": "attack", "value": 10},
    "Glowtail Panther": {"rarity": "Rare", "type": "Golden Egg", "buff_desc": "+8% Coin bonus", "buff_type": "coin", "value": 0.08},
    
    "Astral Phoenix": {"rarity": "Epic", "type": "Celestial Egg", "buff_desc": "5% chance to avoid failure on hard quests", "buff_type": "revive", "value": 0.05},
    "Void Turtle": {"rarity": "Epic", "type": "Celestial Egg", "buff_desc": "+15% defense and massive material yield on expeditions", "buff_type": "defense_material", "value": 0.15},
    "Nebula Dragon": {"rarity": "Legendary", "type": "Celestial Egg", "buff_desc": "+25% total coin multiplier & +15 attack power", "buff_type": "coin_attack", "value": (0.25, 15)},
    "Starlight Celestial Spirit": {"rarity": "Legendary", "type": "Celestial Egg", "buff_desc": "+Coin gain, double rare drops, -10% cooldowns", "buff_type": "ultimate", "value": 0.10}
}

class PetsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="hatch", description="Hatch a pet from your inventory using an egg type.")
    @app_commands.choices(egg_type=[
        app_commands.Choice(name="Common Egg", value="Common Egg"),
        app_commands.Choice(name="Golden Egg", value="Golden Egg"),
        app_commands.Choice(name="Celestial Egg", value="Celestial Egg")
    ])
    async def hatch(self, interaction: discord.Interaction, egg_type: str):
        user_id = str(interaction.user.id)
        data = load_pets_data()
        
        if user_id not in data:
            data[user_id] = {"inventory": [], "active_pet": None, "eggs": {}}

        # Note: You can link this to your economy/item inventory system later. 
        # For now, it lets users hatch based on their available pool!
        
        # Determine roll pools based on egg type
        roll = random.random()
        hatched_pet_name = None

        if egg_type == "Common Egg":
            # ~75% Common, ~20% Uncommon, ~5% Rare
            if roll < 0.75:
                hatched_pet_name = random.choice(["Starlight Slime", "Pebble Crab", "Shadow Mouse"])
            elif roll < 0.95:
                hatched_pet_name = random.choice(["Sunwing Finch", "Crystal Hedgehog"])
            else:
                hatched_pet_name = random.choice(["Ember Fox", "Glowtail Panther"])
                
        elif egg_type == "Golden Egg":
            # ~60% Uncommon, ~30% Rare, ~10% Epic
            if roll < 0.60:
                hatched_pet_name = random.choice(["Sunwing Finch", "Crystal Hedgehog"])
            elif roll < 0.90:
                hatched_pet_name = random.choice(["Ember Fox", "Glowtail Panther"])
            else:
                hatched_pet_name = random.choice(["Astral Phoenix", "Void Turtle"])
                
        elif egg_type == "Celestial Egg":
            # ~70% Epic, ~30% Legendary
            if roll < 0.70:
                hatched_pet_name = random.choice(["Astral Phoenix", "Void Turtle"])
            else:
                hatched_pet_name = random.choice(["Nebula Dragon", "Starlight Celestial Spirit"])

        pet_info = PET_DATABASE[hatched_pet_name]
        
        # Add to user inventory
        data[user_id]["inventory"].append({
            "name": hatched_pet_name,
            "rarity": pet_info["rarity"],
            "buff": pet_info["buff_desc"]
        })
        save_pets_data(data)

        embed = discord.Embed(
            title="🥚 Egg Hatched Successfully!",
            description=f"You cracked open a **{egg_type}** and out popped...",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"✨ {hatched_pet_name} ({pet_info['rarity']})", value=f"**Buff:** {pet_info['buff_desc']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pets", description="View your pet collection and active companion.")
    async def pets(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pets_data()
        
        user_data = data.get(user_id, {"inventory": [], "active_pet": None})
        inventory = user_data["inventory"]
        active_pet = user_data["active_pet"]

        embed = discord.Embed(title=f"🐾 {interaction.user.display_name}'s Pet Collection", color=discord.Color.blurple())
        
        if active_pet:
            embed.add_field(name="🟢 Active Companion", value=f"**{active_pet['name']}** ({active_pet['rarity']})\n*Buff:* {active_pet['buff']}", inline=False)
        else:
            embed.add_field(name="🟢 Active Companion", value="None equipped. Use `/equip` to choose one!", inline=False)

        if not inventory:
            embed.description = "Your inventory is empty! Buy some eggs from the shop and hatch them."
        else:
            pet_list = "\n".join([f"• **{p['name']}** ({p['rarity']}) - *{p['buff']}*" for p in inventory])
            embed.add_field(name=f"📦 All Pets ({len(inventory)})", value=pet_list, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="equip", description="Equip a companion from your inventory to gain its passive buff.")
    async def equip(self, interaction: discord.Interaction, pet_name: str):
        user_id = str(interaction.user.id)
        data = load_pets_data()
        
        user_data = data.get(user_id, {"inventory": [], "active_pet": None})
        
        # Find pet in inventory
        matching_pet = next((p for p in user_data["inventory"] if p["name"].lower() == pet_name.lower()), None)
        
        if not matching_pet:
            await interaction.response.send_message(f"❌ You don't own a pet named **{pet_name}** in your inventory.", ephemeral=True)
            return

        user_data["active_pet"] = matching_pet
        save_pets_data(data)

        await interaction.response.send_message(f"✅ Successfully equipped **{matching_pet['name']}**! Its passive buff is now active.")

async def setup(bot):
    await bot.add_cog(PetsCog(bot))
