import discord
from discord.ext import commands
import random
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, MISC_ITEMS, PET_EGGS, BUNDLES

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

# --- INTERACTIVE RPG ACTION VIEWS ---
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

    @discord.ui.button(label="◀️ Page 2", style=discord.ButtonStyle.primary, custom_id="shop_p2")
    async def p2_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_shop_embed(2)
        await interaction.response.edit_message(embed=embed, view=ShopPaginationView(self.cog, self.user_id, 2))

    @discord.ui.button(label="Page 3 ▶️", style=discord.ButtonStyle.primary, custom_id="shop_p3")
    async def p3_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.cog.get_shop_embed(3)
        await interaction.response.edit_message(embed=embed, view=ShopPaginationView(self.cog, self.user_id, 3))


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

    @discord.app_commands.command(name="profile", description="Check your RPG character stats, gear, and action buttons.")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {}).get("name", "Unknown Biome")
        
        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile & Action Hub", color=discord.Color.blurple())
        embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']}/{p['level'] * 250} XP)\n**Area:** {area} ({biome})", inline=False)
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
        update_player(uid, p)
        await interaction.response.send_message(f"🪓 You collected **{wood}x Wood**!", ephemeral=False)

    async def execute_fish(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        fish_caught = random.randint(1, 4) * p.get("area", 1)
        p["inventory"]["fish"] = p["inventory"].get("fish", 0) + fish_caught
        self._update_quest_progress(p, "fish", fish_caught)
        update_player(uid, p)
        await interaction.response.send_message(f"🎣 You caught **{fish_caught}x Fish**!", ephemeral=False)

    @discord.app_commands.command(name="area", description="View your current area, biomes, unlocks, or travel to a new area.")
    @discord.app_commands.describe(target_area="Area number to travel to")
    async def area(self, interaction: discord.Interaction, target_area: int = None):
        uid = str(interaction.user.id)
        p = get_player(uid)
        current_area = p.get("area", 1)

        if target_area is None:
            embed = discord.Embed(title=f"🗺️ Starlight Biome Progression (Current: Area {current_area})", color=discord.Color.blue())
            lines = []
            for a_num, unlocks in AREA_UNLOCKS.items():
                biome_name = AREA_BIOMES.get(a_num, {}).get("name", "Unknown")
                status = '✅ Current' if a_num == current_area else '✅ Unlocked' if a_num < current_area else '🔒 Locked'
                lines.append(f"**Area {a_num}: {biome_name}** [{status}]\n*🔓 {unlocks}*\n")
            embed.description = "\n".join(lines)
            embed.set_footer(text="Use /area target_area:<num> to travel to unlocked areas!")
            await interaction.response.send_message(embed=embed)
            return

        if target_area > current_area + 1:
            await interaction.response.send_message(f"❌ You cannot skip areas! You are currently in Area {current_area}.", ephemeral=True)
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

    @discord.app_commands.command(name="daily", description="Claim daily reward.")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        bonus = 500 * p.get("area", 1)
        p["wallet"] += bonus
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
            selected = random.choice(QUEST_POOL)
            area = p.get("area", 1)
            p["active_quest"] = {
                "id": selected["id"], "title": selected["title"], "desc": selected["desc"],
                "type": selected["type"], "progress": 0, "target": selected["target"],
                "reward_coins": selected["reward_coins"] * area, "reward_xp": selected["reward_xp"] * area
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

    @discord.app_commands.command(name="hunt", description="Hunt for monsters in your current area biome.")
    async def hunt(self, interaction: discord.Interaction):
        await self.execute_hunt(interaction)

    @discord.app_commands.command(name="adventure", description="Embark on an epic adventure in your current area biome!")
    async def adventure(self, interaction: discord.Interaction):
        await self.execute_adventure(interaction)

    @discord.app_commands.command(name="chop", description="Chop wood in the forest.")
    async def chop(self, interaction: discord.Interaction):
        await self.execute_chop(interaction)

    @discord.app_commands.command(name="fish", description="Fish in the river.")
    async def fish(self, interaction: discord.Interaction):
        await self.execute_fish(interaction)
async def setup(bot):
    await bot.add_cog(RpgCog(bot))
