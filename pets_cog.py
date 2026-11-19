import os
import json
import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
PETS_FILE = os.path.join(DATA_DIR, "pets.json")

# Ensure persistent data directory exists
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


# Incubation durations in seconds
HATCH_TIMES = {
    "Common Egg": 15 * 60,        # 15 minutes
    "Golden Egg": 2 * 60 * 60,    # 2 hours
    "Celestial Egg": 6 * 60 * 60  # 6 hours
}

# Expedition Durations and Rewards
EXPEDITION_TYPES = {
    "Short Patrol": {"duration": 30 * 60, "base_coins": 500, "material_chance": 0.3},
    "Deep Forest Hunt": {"duration": 2 * 60 * 60, "base_coins": 3000, "material_chance": 0.6},
    "Celestial Void Raid": {"duration": 6 * 60 * 60, "base_coins": 12000, "material_chance": 0.9}
}

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

    @app_commands.command(name="hatch", description="Place an egg from your inventory into your incubator to start hatching!")
    @app_commands.choices(egg_type=[
        app_commands.Choice(name="Common Egg (15m)", value="Common Egg"),
        app_commands.Choice(name="Golden Egg (2h)", value="Golden Egg"),
        app_commands.Choice(name="Celestial Egg (6h)", value="Celestial Egg")
    ])
    async def hatch(self, interaction: discord.Interaction, egg_type: str):
        user_id = str(interaction.user.id)
        data = load_pets_data()
        user_data = data.setdefault(user_id, {
            "inventory": [],
            "active_pet": None,
            "incubating": None,
            "expedition": None,
        })

        if user_data.get("incubating"):
            await interaction.response.send_message(
                "❌ Your incubator is already busy! Use `/incubator` to check status or `/claim` when it's finished.",
                ephemeral=True
            )
            return

        player = get_player(user_id)
        inv = player.setdefault("inventory", {})
        egg_key = egg_type.lower()
        owned_eggs = inv.get(egg_key, 0)

        if owned_eggs < 1:
            await interaction.response.send_message(
                f"❌ You don't have a **{egg_type}** in your inventory! Check `/shop` or claim one from a bundle.",
                ephemeral=True
            )
            return

        inv[egg_key] = owned_eggs - 1
        if inv[egg_key] <= 0:
            inv.pop(egg_key, None)
        update_player(user_id, player)

        duration = HATCH_TIMES[egg_type]
        finish_time = time.time() + duration

        user_data["incubating"] = {
            "egg_type": egg_type,
            "finish_time": finish_time
        }
        save_pets_data(data)

        embed = discord.Embed(
            title="🥚 Incubator Started!",
            description=f"You placed a **{egg_type}** into the incubator.\nCheck back in using `/incubator` to monitor its progress!",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Hatch Time: {egg_type}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="incubator", description="Check the status of your currently incubating egg.")
    async def incubator(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.get(user_id, {})
        incubating = user_data.get("incubating")

        embed = discord.Embed(title="⚙️ Starlight Incubator", color=discord.Color.blurple())

        if not incubating:
            embed.description = "Your incubator is currently empty. Use `/hatch` to start incubating an egg!"
        else:
            egg_type = incubating["egg_type"]
            finish_time = incubating["finish_time"]
            remaining = int(finish_time - time.time())

            if remaining <= 0:
                embed.description = f"🎉 Your **{egg_type}** has finished hatching! Run **`/claim`** to see what you got!"
                embed.color = discord.Color.green()
            else:
                mins, secs = divmod(remaining, 60)
                hours, mins = divmod(mins, 60)
                time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
                embed.description = f"Incubating: **{egg_type}**\n⏱️ **Time Remaining:** {time_str}"
                embed.color = discord.Color.gold()

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claim", description="Claim your hatched pet from the incubator.")
    async def claim(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.setdefault(user_id, {
            "inventory": [],
            "active_pet": None,
            "incubating": None,
            "expedition": None,
        })
        incubating = user_data.get("incubating")

        if not incubating:
            await interaction.response.send_message("❌ You don't have anything currently incubating in your incubator!", ephemeral=True)
            return

        remaining = int(incubating["finish_time"] - time.time())
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
            await interaction.response.send_message(f"⏳ Your egg is still hatching! Come back in **{time_str}** or check `/incubator`.", ephemeral=True)
            return

        egg_type = incubating["egg_type"]
        roll = random.random()
        hatched_pet_name = None

        if egg_type == "Common Egg":
            if roll < 0.75:
                hatched_pet_name = random.choice(["Starlight Slime", "Pebble Crab", "Shadow Mouse"])
            elif roll < 0.95:
                hatched_pet_name = random.choice(["Sunwing Finch", "Crystal Hedgehog"])
            else:
                hatched_pet_name = random.choice(["Ember Fox", "Glowtail Panther"])

        elif egg_type == "Golden Egg":
            if roll < 0.60:
                hatched_pet_name = random.choice(["Sunwing Finch", "Crystal Hedgehog"])
            elif roll < 0.90:
                hatched_pet_name = random.choice(["Ember Fox", "Glowtail Panther"])
            else:
                hatched_pet_name = random.choice(["Astral Phoenix", "Void Turtle"])

        elif egg_type == "Celestial Egg":
            if roll < 0.70:
                hatched_pet_name = random.choice(["Astral Phoenix", "Void Turtle"])
            else:
                hatched_pet_name = random.choice(["Nebula Dragon", "Starlight Celestial Spirit"])
        else:
            hatched_pet_name = random.choice(["Starlight Slime", "Pebble Crab", "Shadow Mouse"])

        pet_info = PET_DATABASE[hatched_pet_name]

        user_data["incubating"] = None
        user_data.setdefault("inventory", []).append({
            "name": hatched_pet_name,
            "rarity": pet_info["rarity"],
            "buff": pet_info["buff_desc"]
        })
        save_pets_data(data)

        embed = discord.Embed(
            title="✨ Egg Claimed Successfully!",
            description=f"Your **{egg_type}** hatched into...",
            color=discord.Color.gold()
        )
        embed.add_field(name=f"🐾 {hatched_pet_name} ({pet_info['rarity']})", value=f"**Buff:** {pet_info['buff_desc']}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pets", description="View your pet collection and active companion.")
    async def pets(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.get(user_id, {})
        inventory = user_data.get("inventory", [])
        active_pet = user_data.get("active_pet")

        embed = discord.Embed(title=f"🐾 {interaction.user.display_name}'s Pet Collection", color=discord.Color.blurple())

        if active_pet:
            embed.add_field(name="🟢 Active Companion", value=f"**{active_pet['name']}** ({active_pet['rarity']})\n*Buff:* {active_pet['buff']}", inline=False)
        else:
            embed.add_field(name="🟢 Active Companion", value="None equipped. Use `/equip` to choose one!", inline=False)

        if not inventory:
            embed.description = "Your inventory is empty! Incubate and hatch some eggs to start your collection."
        else:
            pet_list = "\n".join([f"• **{p['name']}** ({p['rarity']}) - *{p['buff']}*" for p in inventory])
            embed.add_field(name=f"📦 All Pets ({len(inventory)})", value=pet_list, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="equip", description="Equip a companion from your inventory to gain its passive buff.")
    async def equip(self, interaction: discord.Interaction, pet_name: str):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.setdefault(user_id, {
            "inventory": [],
            "active_pet": None,
            "incubating": None,
            "expedition": None,
        })
        inventory = user_data.get("inventory", [])
        matching_pet = next((p for p in inventory if p["name"].lower() == pet_name.lower()), None)

        if not matching_pet:
            await interaction.response.send_message(f"❌ You don't own a pet named **{pet_name}** in your inventory.", ephemeral=True)
            return

        user_data["active_pet"] = matching_pet
        save_pets_data(data)

        await interaction.response.send_message(f"✅ Successfully equipped **{matching_pet['name']}**! Its passive buff is now active.")

    @app_commands.command(name="expedition", description="Send your active pet out on a timed adventure for coins and loot!")
    @app_commands.choices(expedition_type=[
        app_commands.Choice(name="Short Patrol (30m)", value="Short Patrol"),
        app_commands.Choice(name="Deep Forest Hunt (2h)", value="Deep Forest Hunt"),
        app_commands.Choice(name="Celestial Void Raid (6h)", value="Celestial Void Raid")
    ])
    async def expedition(self, interaction: discord.Interaction, expedition_type: str):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.get(user_id, {})
        active_pet = user_data.get("active_pet")
        if not active_pet:
            await interaction.response.send_message(
                "❌ You must have an active pet equipped (`/equip`) before sending them on an expedition!",
                ephemeral=True
            )
            return

        if user_data.get("expedition"):
            await interaction.response.send_message(
                "❌ Your pet is already out on an expedition! Check status with `/expedition-status` or claim when ready.",
                ephemeral=True
            )
            return

        base_duration = EXPEDITION_TYPES[expedition_type]["duration"]

        # Apply Sunwing Finch passive buff (-5% duration)
        if active_pet.get("name") == "Sunwing Finch":
            base_duration = int(base_duration * 0.95)

        finish_time = time.time() + base_duration
        user_data["expedition"] = {
            "type": expedition_type,
            "finish_time": finish_time,
            "pet_name": active_pet["name"]
        }
        save_pets_data(data)

        embed = discord.Embed(
            title="🗺️ Pet Expedition Started!",
            description=f"**{active_pet['name']}** has set off on a **{expedition_type}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Companion Buff Active", value=active_pet["buff"], inline=False)
        embed.set_footer(text="Check back when the timer completes to claim your rewards!")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="expedition-status", description="Check the progress of your pet's current expedition.")
    async def expedition_status(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.get(user_id, {})
        expedition = user_data.get("expedition")

        embed = discord.Embed(title="🧭 Expedition Status", color=discord.Color.blurple())

        if not expedition:
            embed.description = "Your pet is resting at home. Use `/expedition` to send them on an adventure!"
        else:
            exp_type = expedition["type"]
            pet_name = expedition["pet_name"]
            remaining = int(expedition["finish_time"] - time.time())

            if remaining <= 0:
                embed.description = f"🎉 **{pet_name}** has returned from their **{exp_type}**!\nRun **`/claim-expedition`** to collect your loot!"
                embed.color = discord.Color.green()
            else:
                mins, secs = divmod(remaining, 60)
                hours, mins = divmod(mins, 60)
                time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
                embed.description = f"🐾 **Pet:** {pet_name}\n🗺️ **Mission:** {exp_type}\n⏱️ **Time Remaining:** {time_str}"
                embed.color = discord.Color.gold()

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="claim-expedition", description="Claim rewards from your completed pet expedition.")
    async def claim_expedition(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        data = load_pets_data()

        user_data = data.setdefault(user_id, {
            "inventory": [],
            "active_pet": None,
            "incubating": None,
            "expedition": None,
        })
        expedition = user_data.get("expedition")

        if not expedition:
            await interaction.response.send_message("❌ Your pet isn't currently on an expedition!", ephemeral=True)
            return

        remaining = int(expedition["finish_time"] - time.time())
        if remaining > 0:
            mins, secs = divmod(remaining, 60)
            hours, mins = divmod(mins, 60)
            time_str = f"{hours}h {mins}m {secs}s" if hours > 0 else f"{mins}m {secs}s"
            await interaction.response.send_message(f"⏳ Your pet is still on their expedition! Return in **{time_str}**.", ephemeral=True)
            return

        exp_type = expedition["type"]
        pet_name = expedition["pet_name"]
        info = EXPEDITION_TYPES.get(exp_type, {"base_coins": 500})

        coins_earned = info["base_coins"]

        # Apply coin bonuses from active pet buffs
        active_pet = user_data.get("active_pet")
        if active_pet:
            active_name = active_pet.get("name")
            if active_name == "Glowtail Panther":
                coins_earned = int(coins_earned * 1.08)
            elif active_name == "Starlight Slime":
                coins_earned = int(coins_earned * 1.02)
            elif active_name == "Nebula Dragon":
                coins_earned = int(coins_earned * 1.25)

        player = get_player(user_id)
        player["wallet"] = player.get("wallet", 0) + coins_earned
        update_player(user_id, player)

        # Clear expedition slot
        user_data["expedition"] = None
        save_pets_data(data)

        embed = discord.Embed(
            title="🎁 Expedition Successful!",
            description=f"**{pet_name}** returned safely from the **{exp_type}** with fantastic loot!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Coins Earned", value=f"🪙 {coins_earned:,} Coins (added to wallet)", inline=True)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(PetsCog(bot))
