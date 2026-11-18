import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

# Biome-specific side quests with distinct loot rewards across all 15 areas
BIOME_QUESTS = {
    "goblin_patrol": {
        "name": "Goblin Woods Patrol",
        "rank": "F",
        "area": 1,
        "type": "hunt",
        "target": 5,
        "desc": "Hunt 5 monsters in Whispering Woods.",
        "coins": 600,
        "xp": 300,
        "loot": {"soft bark": 10, "common lootbox": 1}
    },
    "ruins_scavenger": {
        "name": "Crumbling Ruins Scavenger",
        "rank": "E",
        "area": 2,
        "type": "adventure",
        "target": 3,
        "desc": "Complete 3 adventures in Crumbling Ruins.",
        "coins": 1500,
        "xp": 750,
        "loot": {"ancient stone": 12, "life potion": 5}
    },
    "pearl_diver": {
        "name": "Sunken Riverbank Diver",
        "rank": "E",
        "area": 3,
        "type": "fish",
        "target": 15,
        "desc": "Catch 15 fish along the Sunken Riverbank.",
        "coins": 2500,
        "xp": 1200,
        "loot": {"river pearl": 10, "common egg": 1}
    },
    "meadow_forager": {
        "name": "Glimmering Meadow Forager",
        "rank": "D",
        "area": 4,
        "type": "chop",
        "target": 25,
        "desc": "Gather 25 wood in Glimmering Meadows.",
        "coins": 4000,
        "xp": 1800,
        "loot": {"sweet nectar": 15, "uncommon lootbox": 1}
    },
    "crystal_run": {
        "name": "The Crystal Cavern Run",
        "rank": "D",
        "area": 5,
        "type": "mine",
        "target": 20,
        "desc": "Mine 20 Iron Ore inside Crystal Caverns.",
        "coins": 6500,
        "xp": 2800,
        "loot": {"crystal shard": 15, "dungeon key": 1}
    },
    "shadow_stalker": {
        "name": "Shadowed Thicket Purge",
        "rank": "C",
        "area": 6,
        "type": "hunt",
        "target": 10,
        "desc": "Hunt 10 creatures in the Shadowed Thicket.",
        "coins": 10000,
        "xp": 4200,
        "loot": {"shadow petal": 20, "uncommon lootbox": 2}
    },
    "volcanic_forger": {
        "name": "Volcanic Caldera Expedition",
        "rank": "C",
        "area": 7,
        "type": "craft",
        "target": 1,
        "desc": "Forge or upgrade a piece of gear.",
        "coins": 15000,
        "xp": 6000,
        "loot": {"magma core": 15, "golden egg": 1}
    },
    "gale_harvester": {
        "name": "Windplains Skyward Hunt",
        "rank": "B",
        "area": 8,
        "type": "adventure",
        "target": 5,
        "desc": "Complete 5 adventures in Whispering Windplains.",
        "coins": 22000,
        "xp": 8500,
        "loot": {"gale feather": 25, "rare lootbox": 1}
    },
    "frost_breaker": {
        "name": "Frozen Tundra Survival",
        "rank": "B",
        "area": 9,
        "type": "mine",
        "target": 40,
        "desc": "Mine 40 Iron Ore in the Frozen Tundra.",
        "coins": 32000,
        "xp": 12000,
        "loot": {"everfrost ice": 25, "golden egg": 1, "dungeon key": 2}
    },
    "dragons_peak": {
        "name": "Dragon's Peak Ascend",
        "rank": "A",
        "area": 10,
        "type": "hunt",
        "target": 15,
        "desc": "Slay 15 beasts atop Dragon's Spire.",
        "coins": 50000,
        "xp": 18000,
        "loot": {"dragon scale": 20, "rare lootbox": 2}
    },
    "chrono_stabilizer": {
        "name": "Temporal Rift Anomaly",
        "rank": "A",
        "area": 11,
        "type": "adventure",
        "target": 8,
        "desc": "Complete 8 adventures inside the Temporal Rift.",
        "coins": 75000,
        "xp": 25000,
        "loot": {"chrono dust": 30, "celestial egg": 1}
    },
    "celestial_trial": {
        "name": "Celestial Sanctuary Trial",
        "rank": "S",
        "area": 12,
        "type": "hunt",
        "target": 20,
        "desc": "Hunt 20 guardians in Celestial Sanctuary.",
        "coins": 110000,
        "xp": 35000,
        "loot": {"starlight essence": 30, "epic lootbox": 1}
    },
    "abyssal_descent": {
        "name": "Abyssal Depths Dredge",
        "rank": "S",
        "area": 13,
        "type": "fish",
        "target": 50,
        "desc": "Catch 50 creatures from the Abyssal Depths.",
        "coins": 160000,
        "xp": 50000,
        "loot": {"void matter": 35, "celestial egg": 1, "rare lootbox": 2}
    },
    "world_tree_guardian": {
        "name": "Mythic Overgrowth Harvest",
        "rank": "SS",
        "area": 14,
        "type": "chop",
        "target": 80,
        "desc": "Collect 80 Wood in Mythic Overgrowth.",
        "coins": 230000,
        "xp": 70000,
        "loot": {"world-tree sap": 40, "epic lootbox": 2}
    },
    "singularity_breach": {
        "name": "Transcendence Core Breach",
        "rank": "SSS",
        "area": 15,
        "type": "adventure",
        "target": 12,
        "desc": "Complete 12 adventures at The Transcendence Core.",
        "coins": 350000,
        "xp": 100000,
        "loot": {"singularity core": 25, "epic lootbox": 3, "celestial egg": 2}
    }
}


class BiomeQuestSelect(discord.ui.Select):
    def __init__(self, unlocked_area: int):
        options = []
        for q_id, q in BIOME_QUESTS.items():
            if unlocked_area >= q["area"]:
                loot_preview = ", ".join([f"{qty}x {item.title()}" for item, qty in q["loot"].items()])
                options.append(
                    discord.SelectOption(
                        label=f"[Area {q['area']} | Rank {q['rank']}] {q['name']}",
                        value=q_id,
                        description=f"Loot: {loot_preview}"[:100]
                    )
                )

        super().__init__(
            placeholder="Select an unlocked biome quest to accept...",
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id="starlight:biome_quest_select"
        )

    async def callback(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        q_id = self.values[0]
        q_data = BIOME_QUESTS[q_id]

        unlocked_area = p.get("unlocked_area", p.get("area", 1))
        if unlocked_area < q_data["area"]:
            return await interaction.response.send_message(
                f"❌ You need **Area {q_data['area']}** unlocked to accept this quest!",
                ephemeral=True
            )

        p["active_biome_quest"] = {
            "id": q_id,
            "name": q_data["name"],
            "rank": q_data["rank"],
            "area": q_data["area"],
            "type": q_data["type"],
            "desc": q_data["desc"],
            "progress": 0,
            "target": q_data["target"],
            "coins": q_data["coins"],
            "xp": q_data["xp"],
            "loot": q_data["loot"]
        }
        update_player(uid, p)

        loot_text = ", ".join([f"**{qty}x {item.title()}**" for item, qty in q_data["loot"].items()])
        embed = discord.Embed(
            title=f"📜 Biome Quest Accepted: {q_data['name']} (Rank {q_data['rank']})",
            description=f"**Objective:** {q_data['desc']}\n**Rewards:** 🪙 {q_data['coins']:,} | ⭐ {q_data['xp']:,} XP | 🎁 {loot_text}",
            color=discord.Color.from_str("#F1C40F")
        )
        embed.set_footer(text="Progress tracks automatically alongside your normal /quest!")
        await interaction.response.send_message(embed=embed)


class QuestBoardView(discord.ui.View):
    def __init__(self, user_id: str, unlocked_area: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(BiomeQuestSelect(unlocked_area))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ Open your own quest board with `/questboard`!", ephemeral=True)
            return False
        return True


class QuestsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="questboard", description="View and accept biome-specific side quests with special loot rewards!")
    async def questboard(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        unlocked_area = p.get("unlocked_area", p.get("area", 1))
        active_bq = p.get("active_biome_quest")

        embed = discord.Embed(
            title="📜 Starlight Biome Quest Board",
            description=(
                f"*Highest Unlocked Area: **Tier {unlocked_area}***\n"
                "Biome quests run **separately** from your normal `/quest` and award special loot boxes, eggs, and rare materials!\n"
            ),
            color=discord.Color.from_str("#F1C40F")
        )

        if active_bq:
            loot_str = ", ".join([f"{qty}x {item.title()}" for item, qty in active_bq["loot"].items()])
            embed.add_field(
                name=f"🔥 Active Biome Quest: {active_bq['name']} (Rank {active_bq['rank']})",
                value=(
                    f"*{active_bq['desc']}*\n"
                    f"**Progress:** `{active_bq['progress']}/{active_bq['target']}`\n"
                    f"**Loot:** 🪙 {active_bq['coins']:,} • ⭐ {active_bq['xp']:,} XP • 🎁 {loot_str}\n"
                    f"*(Use `/claimbiomequest` once complete!)*"
                ),
                inline=False
            )

        lines = []
        for q_id, q in BIOME_QUESTS.items():
            loot_preview = ", ".join([f"{qty}x {item.title()}" for item, qty in q["loot"].items()])
            if unlocked_area >= q["area"]:
                lines.append(f"✅ **[Area {q['area']} | Rank {q['rank']}] {q['name']}**\n*Objective:* {q['desc']} | *Loot:* {loot_preview}")
            else:
                lines.append(f"🔒 ~~**[Area {q['area']} | Rank {q['rank']}] {q['name']}**~~ — *Requires Area {q['area']}*")

        embed.add_field(name="Available & Upcoming Biome Quests", value="\n\n".join(lines[:8]), inline=False)
        if len(lines) > 8:
            embed.add_field(name="High-Tier Endgame Quests (Areas 9–15)", value="\n\n".join(lines[8:]), inline=False)

        embed.set_footer(text="Select an unlocked quest from the dropdown below to accept it!")
        await interaction.response.send_message(embed=embed, view=QuestBoardView(uid, unlocked_area))

    @app_commands.command(name="claimbiomequest", description="Claim coins, XP, and special loot from your completed biome quest!")
    async def claimbiomequest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        active_bq = p.get("active_biome_quest")

        if not active_bq:
            return await interaction.response.send_message("❌ You don't have an active biome quest! Pick one from `/questboard`.", ephemeral=True)

        if active_bq["progress"] < active_bq["target"]:
            return await interaction.response.send_message(
                f"⏳ **In Progress:** `{active_bq['progress']}/{active_bq['target']}` — {active_bq['desc']}",
                ephemeral=True
            )

        p["wallet"] += active_bq["coins"]
        p["xp"] += active_bq["xp"]
        inv = p.setdefault("inventory", {})

        loot_lines = []
        for item_name, qty in active_bq["loot"].items():
            inv[item_name] = inv.get(item_name, 0) + qty
            loot_lines.append(f"🎁 +{qty}x **{item_name.title()}**")

        p["active_biome_quest"] = None

        rpg_cog = self.bot.get_cog("RpgCog")
        level_msg = rpg_cog._check_level_up(p) if rpg_cog else ""
        update_player(uid, p)

        embed = discord.Embed(
            title=f"🎉 Biome Quest Completed: {active_bq['name']}!",
            description=(
                f"🪙 **+{active_bq['coins']:,} Coins**\n"
                f"⭐ **+{active_bq['xp']:,} XP**\n"
                + "\n".join(loot_lines)
                + level_msg
            ),
            color=discord.Color.from_str("#F1C40F")
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(QuestsCog(bot))
