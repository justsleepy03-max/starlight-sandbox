import discord
from discord import app_commands
from discord.ext import commands

# Update this import if your database file has a different name (e.g. `import database as db`)
import db

STARLIGHT_GOLD = 0xF1C40F

# Map item IDs/names to their equipment slot: "pet", "sword", "armor", or "horse"
# Add more items/pets here as you expand your RPG catalog
EQUIPPABLE_SLOTS = {
    "slime": "pet",
    "fox": "pet",
    # "wooden_sword": "sword",
    # "leather_armor": "armor",
    # "trail_horse": "horse",
}

# Metadata for the /utility dropdown sub-menu
ITEM_CATALOG = {
    "slime": {"slot": "Pet", "perk": "Starter companion"},
    "fox": {"slot": "Pet", "perk": "Quick-footed companion"},
}

RECIPES_CATALOG = {
    "Gear Tiers (T2–T6)": "Craft higher-tier gear using /craft and /recipes with biome materials & coins.",
    "Perks": "Crafted swords boost hunt coins (+15%) and crafted armor boosts gathering yields (+25%).",
}

AREAS_CATALOG = {
    "Biomes (Areas 1–15)": "Unlock areas by leveling up, travel via /area, and gather area-scaled materials.",
}


def ensure_player_schema(player: dict) -> dict:
    player.setdefault("inventory", {})
    player.setdefault("cooldowns", {})
    player.setdefault("equipment", {})
    for slot in ("sword", "armor", "horse", "pet"):
        player["equipment"].setdefault(slot, None)
    return player


class UtilitySelect(discord.ui.Select):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        options = [
            discord.SelectOption(
                label="Items & Recipes",
                value="items_recipes",
                description="View item perks and crafting/recipe info",
                emoji="⚒️",
            ),
            discord.SelectOption(
                label="Areas (1–15)",
                value="areas",
                description="Check biome progression and gathering info",
                emoji="🗺️",
            ),
            discord.SelectOption(
                label="Server & Bot Stats",
                value="server_stats",
                description="View bot ping, command count, and guild stats",
                emoji="📊",
            ),
        ]
        super().__init__(
            placeholder="Choose a utility view...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        if choice == "items_recipes":
            embed = discord.Embed(
                title="🛠️ Utility — Items & Recipes",
                color=STARLIGHT_GOLD,
            )
            item_lines = [
                f"**{name.replace('_', ' ').title()}** ({info['slot']}) — {info['perk']}"
                for name, info in ITEM_CATALOG.items()
            ]
            recipe_lines = [
                f"**{name}:** {desc}" for name, desc in RECIPES_CATALOG.items()
            ]
            embed.add_field(
                name="Tracked Items",
                value="\n".join(item_lines) if item_lines else "No items configured yet.",
                inline=False,
            )
            embed.add_field(
                name="Crafting & Recipes",
                value="\n".join(recipe_lines) if recipe_lines else "Use `/recipes` and `/craft`.",
                inline=False,
            )

        elif choice == "areas":
            embed = discord.Embed(
                title="🛠️ Utility — Areas & Biomes",
                color=STARLIGHT_GOLD,
            )
            area_lines = [
                f"**{name}:** {desc}" for name, desc in AREAS_CATALOG.items()
            ]
            embed.add_field(
                name="Biome Overview",
                value="\n".join(area_lines),
                inline=False,
            )

        else:  # server_stats
            data = db.load_data()
            total_players = len(data)
            synced_cmds = len(self.bot.tree.get_commands())
            latency_ms = round(self.bot.latency * 1000)

            embed = discord.Embed(
                title="🛠️ Utility — Server & Bot Stats",
                color=STARLIGHT_GOLD,
            )
            embed.add_field(name="Bot Latency", value=f"`{latency_ms} ms`", inline=True)
            embed.add_field(name="Synced Commands", value=f"`{synced_cmds}`", inline=True)
            embed.add_field(name="Saved RPG Profiles", value=f"`{total_players}`", inline=True)
            if interaction.guild:
                embed.add_field(
                    name="Server Members",
                    value=f"`{interaction.guild.member_count or 'N/A'}`",
                    inline=True,
                )

        await interaction.response.edit_message(embed=embed, view=self.view)


class UtilityView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=120)
        self.add_item(UtilitySelect(bot))


class RPGUtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="equip",
        description="Equip a pet or gear item from your inventory without deleting your current one.",
    )
    @app_commands.describe(item="Name of the item or pet from your inventory to equip")
    async def equip(self, interaction: discord.Interaction, item: str):
        key = item.strip().lower().replace(" ", "_")
        slot = EQUIPPABLE_SLOTS.get(key)

        if not slot:
            await interaction.response.send_message(
                f"❌ `{item}` isn't registered as an equippable item or pet yet.",
                ephemeral=True,
            )
            return

        player = ensure_player_schema(db.get_player(interaction.user.id))
        inventory = player["inventory"]

        owned_qty = inventory.get(key, inventory.get(item.strip(), 0))
        if not owned_qty or owned_qty <= 0:
            await interaction.response.send_message(
                f"❌ You don't have **{item}** in your `/inventory`.",
                ephemeral=True,
            )
            return

        previous_item = player["equipment"].get(slot)
        player["equipment"][slot] = key
        db.update_player(interaction.user.id, player)

        prev_label = previous_item.replace("_", " ").title() if previous_item else "None"
        new_label = key.replace("_", " ").title()

        embed = discord.Embed(
            title="🎒 Equipment Updated",
            description=(
                f"**Slot:** `{slot.title()}`\n"
                f"**Equipped:** **{new_label}**\n"
                f"**Replaced:** {prev_label} *(kept safely in your `/inventory`)*"
            ),
            color=STARLIGHT_GOLD,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="utility",
        description="Open a sub-menu for items/recipes, areas, or server stats.",
    )
    async def utility(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛠️ Starlight Utility Menu",
            description="Select an option below to view **Items & Recipes**, **Areas**, or **Server Stats**.",
            color=STARLIGHT_GOLD,
        )
        await interaction.response.send_message(
            embed=embed,
            view=UtilityView(self.bot),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(RPGUtilityCog(bot))
