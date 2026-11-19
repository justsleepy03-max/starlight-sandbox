import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player
from items import ARMORS

AREA_BIOMES = {
    1: "Whispering Woods",
    2: "Crumbling Ruins",
    3: "Sunken Riverbank",
    4: "Glimmering Meadows",
    5: "Crystal Caverns",
    6: "Shadowed Thicket",
    7: "Volcanic Caldera",
    8: "Whispering Windplains",
    9: "Frozen Tundra",
    10: "Dragon’s Spire",
    11: "Temporal Rift",
    12: "Celestial Sanctuary",
    13: "Abyssal Depths",
    14: "Mythic Overgrowth",
    15: "The Transcendence Core",
}

AREA_LEVEL_REQUIREMENTS = {
    1: 1, 2: 3, 3: 6, 4: 9, 5: 12, 6: 15, 7: 18, 8: 21, 9: 24, 10: 27, 11: 30, 12: 33, 13: 36, 14: 39, 15: 42
}

WEAPON_RECIPES = {
    2: {"name": "Briarwood Hunter Bow", "coins": 1500, "wood": 25, "iron ore": 0, "mats": {"soft bark": 5}},
    3: {"name": "Moss-Veined Staff", "coins": 3000, "wood": 40, "iron ore": 0, "mats": {"soft bark": 10}},
    4: {"name": "Damp Dagger of the Depths", "coins": 5500, "wood": 55, "iron ore": 0, "mats": {"ancient stone": 8, "river pearl": 4}},
    5: {"name": "Granite Crag Hammer", "coins": 9000, "wood": 75, "iron ore": 30, "mats": {"ancient stone": 12}},
    6: {"name": "Glacial Frost Spear", "coins": 13500, "wood": 90, "iron ore": 45, "mats": {"river pearl": 12}},
    7: {"name": "Magma Core Greatsword", "coins": 18000, "wood": 105, "iron ore": 70, "mats": {"magma core": 8}},
    8: {"name": "Dune-Scourge Scimitar", "coins": 32000, "wood": 120, "iron ore": 80, "mats": {"magma core": 12, "crystal shard": 6}},
    9: {"name": "Knight's Oath Broadsword", "coins": 65000, "wood": 180, "iron ore": 108, "mats": {"dragon scale": 8, "crystal shard": 10}},
    10: {"name": "Abyssal Tide Trident", "coins": 110000, "wood": 200, "iron ore": 120, "mats": {"dragon scale": 12, "river pearl": 12}},
    11: {"name": "Void Edge", "coins": 180000, "wood": 220, "iron ore": 132, "mats": {"void matter": 8, "dragon scale": 10}},
    12: {"name": "Sunburst Seraph Blade", "coins": 260000, "wood": 240, "iron ore": 144, "mats": {"starlight essence": 10, "void matter": 8}},
    13: {"name": "Temporal Crossbow", "coins": 375000, "wood": 325, "iron ore": 195, "mats": {"starlight essence": 14, "void matter": 10}},
    14: {"name": "Event Horizon Scythe", "coins": 525000, "wood": 350, "iron ore": 210, "mats": {"void matter": 14, "starlight essence": 12}},
    15: {"name": "Starlight Greatsword", "coins": 850000, "wood": 375, "iron ore": 225, "mats": {"singularity core": 8, "void matter": 12, "starlight essence": 12}},
}

MATERIAL_POOLS = {
    "Common / Early": ["wood", "fish", "soft bark", "ancient stone", "river pearl"],
    "Uncommon / Mid": ["iron ore", "sweet nectar", "crystal shard", "shadow petal"],
    "Rare / High-Value": ["magma core", "gale feather", "everfrost ice", "dragon scale"],
    "Mythic / Endgame": ["chrono dust", "starlight essence", "void matter", "world-tree sap", "singularity core"],
}


def get_recipe_for_tier(gear_type: str, target_tier: int) -> dict:
    """Returns a normalized recipe dict {'label', 'coins', 'wood', 'iron ore', 'mats'} for tiers 2-15."""
    if gear_type == "sword" and target_tier in WEAPON_RECIPES:
        base = WEAPON_RECIPES[target_tier]
        return {
            "label": base["name"],
            "coins": base["coins"],
            "wood": base["wood"],
            "iron ore": base["iron ore"],
            "mats": dict(base["mats"]),
        }

    armor_name = ARMORS.get(target_tier, {}).get("name", f"Tier {target_tier} Armor").title()
    if target_tier <= 6:
        coin_map = {2: 1500, 3: 3000, 4: 5500, 5: 9000, 6: 13500}
        wood_map = {2: 25, 3: 40, 4: 55, 5: 75, 6: 90}
        iron_map = {2: 0, 3: 0, 4: 0, 5: 30, 6: 45}
        mats_map = {
            2: {"soft bark": 5},
            3: {"soft bark": 10},
            4: {"ancient stone": 8, "river pearl": 4},
            5: {"ancient stone": 12},
            6: {"river pearl": 12},
        }
    else:
        coin_map = {
            7: 18000, 8: 32000, 9: 65000, 10: 110000,
            11: 180000, 12: 260000, 13: 375000, 14: 525000, 15: 850000
        }
        wood_map = {
            7: 105, 8: 120, 9: 180, 10: 200,
            11: 220, 12: 240, 13: 325, 14: 350, 15: 375
        }
        iron_map = {
            7: 70, 8: 80, 9: 108, 10: 120,
            11: 132, 12: 144, 13: 195, 14: 210, 15: 225
        }
        mats_map = {
            7: {"magma core": 8},
            8: {"magma core": 12, "crystal shard": 6},
            9: {"dragon scale": 8, "crystal shard": 10},
            10: {"dragon scale": 12, "river pearl": 12},
            11: {"void matter": 8, "dragon scale": 10},
            12: {"starlight essence": 10, "void matter": 8},
            13: {"starlight essence": 14, "void matter": 10},
            14: {"void matter": 14, "starlight essence": 12},
            15: {"singularity core": 8, "void matter": 12, "starlight essence": 12},
        }

    return {
        "label": armor_name,
        "coins": coin_map[target_tier],
        "wood": wood_map[target_tier],
        "iron ore": iron_map[target_tier],
        "mats": dict(mats_map[target_tier]),
    }


def build_recipe_embed(page: str) -> discord.Embed:
    if page == "pools":
        embed = discord.Embed(title="🧪 Crafting Material Pools", color=discord.Color.teal())
        for pool_name, items in MATERIAL_POOLS.items():
            embed.add_field(
                name=pool_name,
                value=", ".join(f"`{i}`" for i in items),
                inline=False,
            )
        embed.set_footer(text="Tiers 2–6 use common/early mats • Tiers 7–15 use rare & endgame mats")
        return embed

    if page == "mid":
        tiers = range(7, 12)
        title = "⚒️ Crafting Recipes — Tiers 7–11 (Rare Mats)"
        color = discord.Color.orange()
    elif page == "high":
        tiers = range(12, 16)
        title = "🌌 Crafting Recipes — Tiers 12–15 (Endgame Mats)"
        color = discord.Color.purple()
    else:
        tiers = range(2, 7)
        title = "🪵 Crafting Recipes — Tiers 2–6 (Common Mats)"
        color = discord.Color.green()

    embed = discord.Embed(title=title, color=color)
    for t in tiers:
        r = get_recipe_for_tier("sword", t)
        parts = [f"🪙 {r['coins']:,}", f"{r['wood']}x wood"]
        if r["iron ore"] > 0:
            parts.append(f"{r['iron ore']}x iron ore")
        for mat_name, qty in r["mats"].items():
            parts.append(f"{qty}x {mat_name}")
        embed.add_field(
            name=f"T{t}: {r['label']}",
            value=" • ".join(parts),
            inline=False,
        )
    embed.set_footer(text="Use /craft gear_type:sword target_tier:<num> to forge!")
    return embed


class RecipeSelect(discord.ui.Select):
    def __init__(self, user_id: str):
        self.user_id = user_id
        options = [
            discord.SelectOption(label="Tiers 2–6 (Common Mats)", value="early", emoji="🪵"),
            discord.SelectOption(label="Tiers 7–11 (Rare Mats)", value="mid", emoji="🔥"),
            discord.SelectOption(label="Tiers 12–15 (Endgame Mats)", value="high", emoji="🌌"),
            discord.SelectOption(label="Material Rarity Pools", value="pools", emoji="🧪"),
        ]
        super().__init__(placeholder="Choose a recipe tier or pool...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This recipe menu isn't yours!", ephemeral=True)
            return
        embed = build_recipe_embed(self.values[0])
        await interaction.response.edit_message(embed=embed, view=self.view)


class RecipeView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=120)
        self.add_item(RecipeSelect(user_id))


class CraftingCog(commands.Cog):
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
            p["max_hp"] = p.get("max_hp", 100) + 20
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
            new_biome_name = AREA_BIOMES.get(highest_eligible, "Unknown Zone")
            messages.append(f"\n🚀 **AREA UNLOCKED!** Your level progression automatically unlocked **Area {highest_eligible} ({new_biome_name})**!")

        return "".join(messages)

    @app_commands.command(name="materials", description="List crafting material pools, biome sources, and your current stock.")
    async def materials(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})

        embed = discord.Embed(
            title="🧪 Starlight Crafting Materials List",
            description="Rarity pools and how much you currently hold in your inventory:",
            color=discord.Color.teal(),
        )

        for pool_name, pool_items in MATERIAL_POOLS.items():
            lines = []
            for mat in pool_items:
                owned = inv.get(mat, 0)
                lines.append(f"`{mat}` *(x{owned:,})*")
            embed.add_field(
                name=pool_name,
                value=", ".join(lines),
                inline=False,
            )

        embed.set_footer(text="Use /recipes to see exact tier costs • Use /craft to forge")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="recipes", description="View weapon crafting recipes and material rarity pools.")
    @app_commands.describe(view="Optional section to jump straight to")
    @app_commands.choices(view=[
        app_commands.Choice(name="Tiers 2–6 (Common)", value="early"),
        app_commands.Choice(name="Tiers 7–11 (Rare)", value="mid"),
        app_commands.Choice(name="Tiers 12–15 (Endgame)", value="high"),
        app_commands.Choice(name="Material Pools", value="pools"),
    ])
    async def recipes(self, interaction: discord.Interaction, view: str = "early"):
        embed = build_recipe_embed(view)
        await interaction.response.send_message(embed=embed, view=RecipeView(str(interaction.user.id)))

    @app_commands.command(name="craft", description="Craft higher tier swords and armor using your gathered materials.")
    @app_commands.describe(gear_type="Choose whether to craft a sword or armor", target_tier="Target tier to forge (2 to 15)")
    @app_commands.choices(gear_type=[
        app_commands.Choice(name="Sword", value="sword"),
        app_commands.Choice(name="Armor", value="armor"),
    ])
    async def craft(self, interaction: discord.Interaction, gear_type: str, target_tier: int):
        uid = str(interaction.user.id)
        p = get_player(uid)

        if target_tier < 2 or target_tier > 15:
            await interaction.response.send_message("❌ You can forge gear tiers from **Tier 2 up to Tier 15**!", ephemeral=True)
            return

        current_key = f"{gear_type}_tier"
        current_tier = p.get(current_key, 1)

        if target_tier <= current_tier:
            await interaction.response.send_message(
                f"❌ Your current {gear_type} is already Tier {current_tier}! You can only craft higher tiers.",
                ephemeral=True,
            )
            return

        if target_tier != current_tier + 1:
            await interaction.response.send_message(
                f"❌ You must forge gear sequentially! Your next available tier is **Tier {current_tier + 1}**.",
                ephemeral=True,
            )
            return

        recipe = get_recipe_for_tier(gear_type, target_tier)
        coin_cost = recipe["coins"]
        wood_cost = recipe["wood"]
        iron_cost = recipe["iron ore"]
        extra_mats = recipe["mats"]

        inv = p.setdefault("inventory", {})

        if p.get("wallet", 0) < coin_cost:
            await interaction.response.send_message(
                f"❌ Not enough coins! You need **🪙 {coin_cost:,}** coins to forge Tier {target_tier}.",
                ephemeral=True,
            )
            return

        if inv.get("wood", 0) < wood_cost:
            await interaction.response.send_message(
                f"❌ Not enough wood! You need **{wood_cost}x Wood** (You have {inv.get('wood', 0)}).",
                ephemeral=True,
            )
            return

        if iron_cost > 0 and inv.get("iron ore", 0) < iron_cost:
            await interaction.response.send_message(
                f"❌ Not enough iron ore! You need **{iron_cost}x Iron Ore** (You have {inv.get('iron ore', 0)}).",
                ephemeral=True,
            )
            return

        for mat_name, mat_qty in extra_mats.items():
            owned_qty = inv.get(mat_name, 0)
            if owned_qty < mat_qty:
                await interaction.response.send_message(
                    f"❌ Not enough **{mat_name.title()}**! You need **{mat_qty}x {mat_name.title()}** (You have {owned_qty}).",
                    ephemeral=True,
                )
                return

        p["wallet"] -= coin_cost
        inv["wood"] -= wood_cost
        if iron_cost > 0:
            inv["iron ore"] -= iron_cost
            if inv["iron ore"] <= 0:
                inv.pop("iron ore", None)
        if inv["wood"] <= 0:
            inv.pop("wood", None)

        for mat_name, mat_qty in extra_mats.items():
            inv[mat_name] -= mat_qty
            if inv[mat_name] <= 0:
                inv.pop(mat_name, None)

        p[current_key] = target_tier
        p[f"{gear_type}_origin"] = "crafted"

        self._update_quest_progress(p, "craft", 1)
        level_msg = self._check_level_up(p)
        update_player(uid, p)

        emoji = "⚔️" if gear_type == "sword" else "🛡️"
        bonus_perk = "(+15% Hunt Coins)" if gear_type == "sword" else "(+25% Gathering Yield)"

        cost_parts = [f"🪙 {coin_cost:,} coins", f"{wood_cost}x Wood"]
        if iron_cost > 0:
            cost_parts.append(f"{iron_cost}x Iron Ore")
        for mat_name, mat_qty in extra_mats.items():
            cost_parts.append(f"{mat_qty}x {mat_name.title()}")

        await interaction.response.send_message(
            f"🎉 **FORGING SUCCESSFUL!** You forged **{recipe['label']} (Tier {target_tier} {gear_type.title()})** {emoji}!\n"
            f"*Perk Active:* **{bonus_perk}**\n"
            f"*Costs paid:* {', '.join(cost_parts)}{level_msg}"
        )


async def setup(bot):
    await bot.add_cog(CraftingCog(bot))
