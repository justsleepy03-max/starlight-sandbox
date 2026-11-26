import random
import time
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

COMMISSION_RESET_SECONDS = 24 * 60 * 60

RECIPES = {
    "grilled river trout": {
        "area_req": 5,
        "ingredients": {"fish": 3, "wood": 2},
        "heal": 60,
        "buff_type": "gather_yield",
        "buff_value": 0.25,
        "buff_duration": 1800,  # 30 mins
        "buff_label": "+25% Gathering Yield (30m)",
    },
    "nectar glazed skewer": {
        "area_req": 5,
        "ingredients": {"fish": 2, "sweet nectar": 2, "wood": 2},
        "heal": 90,
        "buff_type": "hunt_coins",
        "buff_value": 0.20,
        "buff_duration": 1800,  # 30 mins
        "buff_label": "+20% Hunt Coins (30m)",
    },
    "crystal broth": {
        "area_req": 5,
        "ingredients": {"river pearl": 2, "crystal shard": 2, "fish": 2},
        "heal": 140,
        "buff_type": "adventure_xp",
        "buff_value": 0.20,
        "buff_duration": 2700,  # 45 mins
        "buff_label": "+20% Adventure XP (45m)",
    },
    "hearty miner stew": {
        "area_req": 5,
        "ingredients": {"fish": 4, "ancient stone": 2, "sweet nectar": 1},
        "heal": 180,
        "buff_type": "defense_boost",
        "buff_value": 0.15,
        "buff_duration": 2700,  # 45 mins
        "buff_label": "+15% Damage Reduction (45m)",
    },
}

COMMISSION_TEMPLATES = [
    {
        "id": "comm_trout",
        "title": "Tavern Catch Order",
        "dish": "grilled river trout",
        "target": 2,
        "reward_coins": 400,
        "reward_xp": 350,
    },
    {
        "id": "comm_skewer",
        "title": "Sweet Field Ration",
        "dish": "nectar glazed skewer",
        "target": 2,
        "reward_coins": 550,
        "reward_xp": 450,
    },
    {
        "id": "comm_broth",
        "title": "Cavern Warmth Request",
        "dish": "crystal broth",
        "target": 1,
        "reward_coins": 650,
        "reward_xp": 550,
    },
    {
        "id": "comm_stew",
        "title": "Deep Vein Provisions",
        "dish": "hearty miner stew",
        "target": 1,
        "reward_coins": 750,
        "reward_xp": 650,
    },
]


def get_active_food_buff(p: dict) -> dict | None:
    """Helper any cog can import to check if the player has an active food buff."""
    buff = p.get("active_food_buff")
    if not isinstance(buff, dict):
        return None
    if time.time() >= float(buff.get("expires_at", 0)):
        p["active_food_buff"] = None
        return None
    return buff


def ensure_daily_commissions(p: dict) -> dict:
    now = time.time()
    state = p.get("daily_cooking_commissions")
    if (
        not isinstance(state, dict)
        or now - float(state.get("assigned_at", 0)) >= COMMISSION_RESET_SECONDS
        or not state.get("tasks")
    ):
        chosen = random.sample(COMMISSION_TEMPLATES, k=3)
        tasks = [
            {
                "id": tpl["id"],
                "title": tpl["title"],
                "dish": tpl["dish"],
                "progress": 0,
                "target": tpl["target"],
                "reward_coins": tpl["reward_coins"],
                "reward_xp": tpl["reward_xp"],
                "claimed": False,
            }
            for tpl in chosen
        ]
        state = {
            "assigned_at": now,
            "tasks": tasks,
            "bonus_claimed": False,
        }
        p["daily_cooking_commissions"] = state
    return state


class PrepareDishSelect(discord.ui.Select):
    def __init__(self, parent_view: "KitchenHubView"):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=f"Cook {name.title()}",
                value=name,
                description=f"+{data['heal']} HP | {data['buff_label']}"[:100],
                emoji="🍳",
            )
            for name, data in RECIPES.items()
        ]
        super().__init__(
            placeholder="🍳 Pick a dish to prepare (1x)...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="kitchen_prepare_select",
            row=1,
        )

    async def callback(self, interaction: discord.Interaction):
        uid = str(self.parent_view.user_id)
        p = get_player(uid)
        key = self.values[0]
        recipe = RECIPES[key]

        inv = p.setdefault("inventory", {})
        for ing, req_qty in recipe["ingredients"].items():
            if int(inv.get(ing, 0)) < req_qty:
                await interaction.response.send_message(
                    f"❌ Missing ingredients! You need **{req_qty}x {ing.title()}** (have **{inv.get(ing, 0)}**).",
                    ephemeral=True,
                )
                return

        for ing, req_qty in recipe["ingredients"].items():
            inv[ing] = int(inv.get(ing, 0)) - req_qty
            if inv[ing] <= 0:
                del inv[ing]

        dishes = p.setdefault("cooked_dishes", {})
        dishes[key] = int(dishes.get(key, 0)) + 1

        state = ensure_daily_commissions(p)
        for task in state["tasks"]:
            if not task["claimed"] and task["dish"] == key:
                task["progress"] = min(task["target"], int(task["progress"]) + 1)

        update_player(uid, p)
        embed = self.parent_view.cog.build_recipes_embed(p, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self.parent_view)
        await interaction.followup.send(
            f"🍳 Cooked **1x {key.title()}**! Pick it in the **Eat** dropdown below to activate **{recipe['buff_label']}**.",
            ephemeral=True,
        )


class EatDishSelect(discord.ui.Select):
    def __init__(self, parent_view: "KitchenHubView"):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(
                label=f"Eat {name.title()}",
                value=name,
                description=f"Heal +{data['heal']} HP & {data['buff_label']}"[:100],
                emoji="🍽️",
            )
            for name, data in RECIPES.items()
        ]
        super().__init__(
            placeholder="🍽️ Pick a cooked dish to eat & buff...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="kitchen_eat_select",
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        uid = str(self.parent_view.user_id)
        p = get_player(uid)
        key = self.values[0]
        recipe = RECIPES[key]

        dishes = p.setdefault("cooked_dishes", {})
        if int(dishes.get(key, 0)) < 1:
            await interaction.response.send_message(
                f"❌ You don't have any **{key.title()}** cooked yet! Prepare one above first.",
                ephemeral=True,
            )
            return

        dishes[key] -= 1
        if dishes[key] <= 0:
            del dishes[key]

        max_hp = int(p.get("max_hp", 100))
        cur_hp = int(p.get("hp", max_hp))
        p["hp"] = min(max_hp, cur_hp + int(recipe["heal"]))

        p["active_food_buff"] = {
            "dish": key,
            "type": recipe["buff_type"],
            "value": recipe["buff_value"],
            "label": recipe["buff_label"],
            "expires_at": time.time() + int(recipe["buff_duration"]),
        }

        update_player(uid, p)
        embed = self.parent_view.cog.build_recipes_embed(p, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self.parent_view)
        await interaction.followup.send(
            f"🍽️ Ate **{key.title()}**! Restored **+{recipe['heal']} HP** ({p['hp']}/{max_hp} HP) & activated **{recipe['buff_label']}**!",
            ephemeral=True,
        )


class KitchenHubView(discord.ui.View):
    def __init__(self, cog: "CookingQuestsCog", user_id: int):
        super().__init__(timeout=180)
        self.cog = cog
        self.user_id = user_id
        self.add_item(PrepareDishSelect(self))
        self.add_item(EatDishSelect(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This kitchen board isn't yours! Run `/kitchen` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(label="Recipes & Buffs", style=discord.ButtonStyle.primary, custom_id="cook_recipes", row=0)
    async def recipes_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        p = get_player(str(self.user_id))
        embed = self.cog.build_recipes_embed(p, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Daily Commissions", style=discord.ButtonStyle.success, custom_id="cook_comms", row=0)
    async def comms_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(self.user_id)
        p = get_player(uid)
        ensure_daily_commissions(p)
        update_player(uid, p)
        embed = self.cog.build_commissions_embed(p, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Claim Commissions", style=discord.ButtonStyle.secondary, custom_id="cook_claim", row=0)
    async def claim_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(self.user_id)
        p = get_player(uid)
        state = ensure_daily_commissions(p)

        coins_gained = 0
        xp_gained = 0
        claimed_titles = []

        for task in state["tasks"]:
            if not task["claimed"] and task["progress"] >= task["target"]:
                task["claimed"] = True
                coins_gained += int(task["reward_coins"])
                xp_gained += int(task["reward_xp"])
                claimed_titles.append(task["title"])

        bonus_msg = ""
        all_done = all(t["claimed"] for t in state["tasks"])
        if all_done and not state.get("bonus_claimed"):
            state["bonus_claimed"] = True
            coins_gained += 600
            xp_gained += 500
            inv = p.setdefault("inventory", {})
            inv["rare lootbox"] = int(inv.get("rare lootbox", 0)) + 1
            bonus_msg = "\n🌟 **All 3 Daily Commissions Complete!** Bonus: **+🪙 600**, **+⭐ 500 XP**, and **1x Rare Lootbox**!"

        if not claimed_titles and not bonus_msg:
            await interaction.response.send_message(
                "⏳ No completed cooking commissions ready to claim yet! Prepare dishes using the dropdown below.",
                ephemeral=True,
            )
            return

        p["wallet"] = int(p.get("wallet", 0)) + coins_gained
        p["xp"] = int(p.get("xp", 0)) + xp_gained
        update_player(uid, p)

        embed = self.cog.build_commissions_embed(p, interaction.user.display_name)
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            f"✅ Claimed **{len(claimed_titles)}** commission(s): **+🪙 {coins_gained:,}** coins & **+⭐ {xp_gained:,}** XP!{bonus_msg}",
            ephemeral=True,
        )


class CookingQuestsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _has_area5_access(self, p: dict) -> bool:
        return max(int(p.get("area", 1)), int(p.get("unlocked_area", 1))) >= 5

    def build_recipes_embed(self, p: dict, display_name: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"🍳 {display_name}'s Kitchen & Food Buffs",
            description="Use the buttons & dropdowns below to prepare dishes, eat for buffs, and claim daily commissions!",
            color=discord.Color.orange(),
        )
        inv = p.get("inventory", {})
        dishes = p.get("cooked_dishes", {})

        for name, data in RECIPES.items():
            ing_str = ", ".join(
                f"{qty}x {ing.title()} ({inv.get(ing, 0)})"
                for ing, qty in data["ingredients"].items()
            )
            owned = int(dishes.get(name, 0))
            embed.add_field(
                name=f"🍲 {name.title()} (Cooked: {owned})",
                value=f"**Buff:** {data['buff_label']} • **Heals:** +{data['heal']} HP\n**Needs:** {ing_str}",
                inline=False,
            )

        active_buff = get_active_food_buff(p)
        if active_buff:
            mins_left = max(1, int((active_buff["expires_at"] - time.time()) // 60))
            embed.set_footer(text=f"Active Buff: {active_buff['label']} • {mins_left}m remaining")
        else:
            embed.set_footer(text="No active food buff • Select a cooked dish below to eat")
        return embed

    def build_commissions_embed(self, p: dict, display_name: str) -> discord.Embed:
        state = ensure_daily_commissions(p)
        embed = discord.Embed(
            title=f"📋 {display_name}'s Daily Cooking Commissions",
            description="Complete all 3 daily orders for a **600-coin + 1x Rare Lootbox** completion bonus!",
            color=discord.Color.gold(),
        )
        for task in state["tasks"]:
            status = "✅ Claimed" if task["claimed"] else ("🎁 Ready!" if task["progress"] >= task["target"] else "⏳ In Progress")
            embed.add_field(
                name=f"{task['title']} ({status})",
                value=(
                    f"Prepare **{task['target']}x {task['dish'].title()}** (`{task['progress']}/{task['target']}`)\n"
                    f"Reward: +🪙 {task['reward_coins']:,} • +⭐ {task['reward_xp']:,} XP"
                ),
                inline=False,
            )
        remaining = max(0, int(COMMISSION_RESET_SECONDS - (time.time() - float(state["assigned_at"]))))
        hrs, rem = divmod(remaining, 3600)
        mins, _ = divmod(rem, 60)
        embed.set_footer(text=f"Resets in {hrs}h {mins}m")
        return embed

    @app_commands.command(name="kitchen", description="Open your interactive recipe book, food buffs & daily cooking quests.")
    async def kitchen(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._has_area5_access(p):
            await interaction.response.send_message(
                "🔒 Kitchen & Cooking Commissions unlock at **Area 5 (Crystal Caverns)**!",
                ephemeral=True,
            )
            return

        ensure_daily_commissions(p)
        update_player(uid, p)
        embed = self.build_recipes_embed(p, interaction.user.display_name)
        view = KitchenHubView(self, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(CookingQuestsCog(bot))
