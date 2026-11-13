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

# Area biomes and exclusive thematic drops
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

    @discord.app_commands.command(name="ping", description="Test if the RPG cog is working.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong! Starlight RPG engine is active!")

    @discord.app_commands.command(name="help", description="View all available Starlight RPG commands and categories.")
    @discord.app_commands.describe(category="Filter by category (general, rpg, crafting, pets, casino)")
    async def help_command(self, interaction: discord.Interaction, category: str = None):
        category = category.lower() if category else None
        
        if category == "general":
            embed = discord.Embed(title="❓ Starlight Help - General & Economy", color=discord.Color.blue())
            embed.add_field(name="Economy & Stats", value="`/profile` - Stats\n`/bal` - Balances\n`/deposit` / `/withdraw` - Bank\n`/daily` - Daily rewards\n`/shop` & `/buy` - Vendor", inline=False)
        elif category == "rpg":
            embed = discord.Embed(title="❓ Starlight Help - RPG & Exploration", color=discord.Color.green())
            embed.add_field(name="Combat & Quests", value="`/hunt` - Hunt\n`/adventure` - Adventure\n`/enchant` - Upgrade Gear (Area 2+)\n`/dungeon` - Raid Dungeons\n`/area` - Areas (Biomes)\n`/quest` & `/claimquest` - Quests\n`/heal` - Heal HP", inline=False)
        elif category == "casino":
            embed = discord.Embed(title="🎰 Starlight Help - Mini Casino (Area 5+)", color=discord.Color.gold())
            embed.add_field(name="Games of Chance", value="`/coinflip` - Double or nothing\n`/multidice` - Dice battle\n`/slots` - Slot machine", inline=False)
        elif category in ["crafting", "pets"]:
            embed = discord.Embed(title="❓ Starlight Help - Crafting & Pets", color=discord.Color.purple())
            embed.add_field(name="Work & Companions", value="`/chop`, `/fish`, `/mine`, `/farm`, `/cook`\n`/hatch`, `/pets`, `/petadventure` (Area 12+)\n`/inventory`", inline=False)
        else:
            embed = discord.Embed(title="✨ Starlight RPG - Command Directory", color=discord.Color.gold())
            embed.description = "Use `/help category:<name>` for specific lists (`general`, `rpg`, `casino`, `crafting`, `pets`)!"
            embed.add_field(name="📂 Categories", value="• **general**\n• **rpg**\n• **casino**\n• **crafting**\n• **pets**", inline=False)
            embed.set_footer(text="Starlight Sandbox • Built for Epic RPG 1:1 Parity")

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="profile", description="Check your RPG character stats, level, and gear.")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        biome = AREA_BIOMES.get(area, {}).get("name", "Unknown Biome")
        
        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile", color=discord.Color.blurple())
        embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']}/{p['level'] * 250} XP)\n**Area:** {area} ({biome})", inline=False)
        embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
        embed.add_field(name="GEAR", value=f"⚔️ **Sword Tier:** {p.get('sword_tier', 1)}\n🛡️ **Armor Tier:** {p.get('armor_tier', 1)}", inline=False)
        embed.add_field(name="CURRENCY", value=f"🪙 **Wallet:** {p['wallet']:,}\n🏛️ **Bank:** {p['bank']:,}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="bal", description="Check your wallet and bank coin balances.")
    async def bal(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        embed = discord.Embed(title=f"🪙 {interaction.user.display_name}'s Balance", color=discord.Color.gold())
        embed.add_field(name="Bank & Wallet", value=f"🪙 **Wallet:** {p['wallet']:,} coins\n🏛️ **Bank:** {p['bank']:,} coins", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="deposit", description="Deposit coins from your wallet into the bank.")
    @discord.app_commands.describe(amount="Amount to deposit (or type 'all')")
    async def deposit(self, interaction: discord.Interaction, amount: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        dep_amount = p["wallet"] if amount.lower() == "all" else int(amount)
        if dep_amount <= 0 or p["wallet"] < dep_amount:
            await interaction.response.send_message("❌ Invalid deposit amount or insufficient funds.", ephemeral=True)
            return
        p["wallet"] -= dep_amount
        p["bank"] += dep_amount
        update_player(uid, p)
        await interaction.response.send_message(f"🏛️ Successfully deposited **🪙 {dep_amount:,} coins** into your bank!")

    @discord.app_commands.command(name="withdraw", description="Withdraw coins from your bank to your wallet.")
    @discord.app_commands.describe(amount="Amount to withdraw (or type 'all')")
    async def withdraw(self, interaction: discord.Interaction, amount: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        wit_amount = p["bank"] if amount.lower() == "all" else int(amount)
        if wit_amount <= 0 or p["bank"] < wit_amount:
            await interaction.response.send_message("❌ Invalid withdrawal amount or insufficient bank funds.", ephemeral=True)
            return
        p["bank"] -= wit_amount
        p["wallet"] += wit_amount
        update_player(uid, p)
        await interaction.response.send_message(f"🪙 Successfully withdrew **🪙 {wit_amount:,} coins** into your wallet!")

    @discord.app_commands.command(name="area", description="View your current area, biomes, unlocks, or travel to a new area.")
    @discord.app_commands.describe(target_area="Area number to travel to")
    async def area(self, interaction: discord.Interaction, target_area: int = None):
        uid = str(interaction.user.id)
        p = get_player(uid)
        current_area = p.get("area", 1)

        if target_area is None:
            embed = discord.Embed(title=f"🗺️ Starlight Biome & Area Progression (Current: Area {current_area})", color=discord.Color.blue())
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
        await interaction.response.send_message(f"🚀 Successfully traveled to **Area {target_area} ({new_biome})**! New biome drops and scaling unlocked.")

    @discord.app_commands.command(name="enchant", description="Upgrade your sword or armor using gathered materials (Unlocked in Area 2+).")
    @discord.app_commands.describe(gear_type="Choose 'sword' or 'armor'")
    @discord.app_commands.choices(gear_type=[
        discord.app_commands.Choice(name="Sword", value="sword"),
        discord.app_commands.Choice(name="Armor", value="armor")
    ])
    async def enchant(self, interaction: discord.Interaction, gear_type: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        if p.get("area", 1) < 2:
            await interaction.response.send_message("❌ Enchanting is locked until **Area 2**! Use `/area` to progress.", ephemeral=True)
            return
            
        tier_key = f"{gear_type}_tier"
        current_tier = p.get(tier_key, 1)
        wood_cost = current_tier * 5
        ore_cost = current_tier * 3
        
        inv = p.get("inventory", {})
        if inv.get("wood", 0) < wood_cost or inv.get("iron_ore", 0) < ore_cost:
            await interaction.response.send_message(f"❌ Upgrading your {gear_type} to Tier {current_tier + 1} requires **{wood_cost}x Wood** and **{ore_cost}x Iron Ore**! Check `/inventory`.", ephemeral=True)
            return
            
        inv["wood"] -= wood_cost
        inv["iron_ore"] -= ore_cost
        p[tier_key] = current_tier + 1
        
        if gear_type == "sword":
            p["max_hp"] += 10
        update_player(uid, p)
        
        await interaction.response.send_message(f"✨ **SUCCESSFUL ENCHANT!** Your **{gear_type.title()}** was upgraded to **Tier {current_tier + 1}**!")

    @discord.app_commands.command(name="dungeon", description="Raid a dangerous dungeon using a Dungeon Key for massive loot (Area 3+).")
    async def dungeon(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        if p.get("area", 1) < 3:
            await interaction.response.send_message("❌ Dungeons are locked until **Area 3**!", ephemeral=True)
            return
            
        if p.get("inventory", {}).get("dungeon key", 0) < 1:
            await interaction.response.send_message("❌ You need a **Dungeon Key** from `/shop` page 1 to raid a dungeon!", ephemeral=True)
            return
            
        p["inventory"]["dungeon key"] -= 1
        if p["inventory"]["dungeon key"] <= 0:
            del p["inventory"]["dungeon key"]
            
        area = p.get("area", 1)
        reward_coins = random.randint(2500, 6000) * area
        reward_xp = random.randint(1200, 3000) * area
        
        p["wallet"] += reward_coins
        p["xp"] += reward_xp
        p["inventory"]["rare lootbox"] = p["inventory"].get("rare lootbox", 0) + 1
        
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        embed = discord.Embed(title="🏰 Dungeon Raid Cleared!", description=f"You braved the dark depths, defeated the dungeon boss, and emerged victorious!", color=discord.Color.gold())
        embed.add_field(name="RAID SPOILS", value=f"🪙 Coins: +{reward_coins:,}\n⭐ XP: +{reward_xp:,}\n📦 Loot: +1x Rare Lootbox{level_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="hunt", description="Hunt for monsters in your current area biome to gain XP, coins, and rare biome drops.")
    async def hunt(self, interaction: discord.Interaction):
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
        
        embed = discord.Embed(title=f"⚔️ Hunt in {biome['name']} (Area {area})", description="You fought courageously through the biome and secured rare loot!", color=discord.Color.green())
        embed.add_field(name="REWARDS", value=f"🪙 Coins: +{earned_coins:,}\n⭐ XP: +{earned_xp:,}\n🌿 Biome Drop: +{drop_qty}x {biome_drop.title()}{level_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="adventure", description="Embark on an epic adventure in your current area biome!")
    async def adventure(self, interaction: discord.Interaction):
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
        
        embed = discord.Embed(title=f"🗺️ Epic Adventure in {biome['name']} (Area {area})", description="You adventured deep into the regional biome and triumphed over a miniboss!", color=discord.Color.orange())
        embed.add_field(name="REWARDS", value=f"🪙 Coins: +{earned_coins:,}\n⭐ XP: +{earned_xp:,}\n🌟 Biome Drop: +{drop_qty}x {biome_drop.title()}{level_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="shop", description="View the Starlight RPG shop catalog.")
    @discord.app_commands.describe(page="Shop page number (1, 2, or 3 for Starlight Bundles)")
    async def shop(self, interaction: discord.Interaction, page: int = 1):
        if page == 1:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 1/3 (Essentials)", color=discord.Color.blue())
            embed.description = "🌟 **STARLIGHT VENDOR:** Browse essential gear and supplies."
            items_text = "🧪 **life potion** | 🪙 25\n🛡️ **basic armor** | 🪙 200\n⚔️ **basic sword** | 🪙 150\n🐎 **basic horse** | 🪙 500\n🔑 **dungeon key** | 🪙 5,000\n🌱 **seed** | 🪙 4,000"
            embed.add_field(name="Catalog", value=items_text, inline=False)
        elif page == 2:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 2/3 (Lootboxes & Eggs)", color=discord.Color.blue())
            embed.description = "🌟 **STARLIGHT VENDOR:** Companion eggs and boxes! Use `/hatch` after buying an egg."
            items_text = "📦 **common lootbox** | 🪙 800\n📦 **uncommon lootbox** | 🪙 6,000\n📦 **rare lootbox** | 🪙 40,000\n📦 **epic lootbox** | 🪙 150,000\n\n🥚 **common egg** | 🪙 1,000\n🥚 **golden egg** | 🪙 15,000\n🥚 **celestial egg** | 🪙 75,000"
            embed.add_field(name="Catalog", value=items_text, inline=False)
        else:
            embed = discord.Embed(title="✨ Starlight Shop - Page 3/3 (Exclusive Bundles)", color=discord.Color.purple())
            bundles_text = "\n\n".join([f"🎁 **{b_name}** | 🪙 {data['price']}\n*Contents: {', '.join(data['contents'].keys())}*" for b_name, data in BUNDLES.items()])
            embed.add_field(name="Starlight Exclusive Bundles", value=bundles_text, inline=False)
        embed.set_footer(text="Use /buy item_name:<name> to purchase anything!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="buy", description="Purchase items, gear, or Starlight bundles from the shop.")
    @discord.app_commands.describe(item_name="Exact name of the item or bundle you want to buy")
    async def buy(self, interaction: discord.Interaction, item_name: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        item_name = item_name.lower()
        price = MISC_ITEMS.get(item_name, {}).get("price") or PET_EGGS.get(item_name, {}).get("price") or BUNDLES.get(item_name, {}).get("price")
        if not price:
            await interaction.response.send_message(f"❌ Unknown item `{item_name}`! Check `/shop`.", ephemeral=True)
            return
        if p["wallet"] < price:
            await interaction.response.send_message(f"❌ You need 🪙 {price:,} coins, but your wallet has 🪙 {p['wallet']:,}.", ephemeral=True)
            return
        p["wallet"] -= price
        p["inventory"][item_name] = p["inventory"].get(item_name, 0) + 1
        update_player(uid, p)
        await interaction.response.send_message(f"🎉 Successfully purchased **{item_name.title()}** for 🪙 {price:,} coins!")

    @discord.app_commands.command(name="hatch", description="Hatch an egg from your inventory into a companion pet!")
    @discord.app_commands.describe(egg_name="common egg, golden egg, or celestial egg")
    async def hatch(self, interaction: discord.Interaction, egg_name: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        egg_name = egg_name.lower()
        if egg_name not in ["common egg", "golden egg", "celestial egg"]:
            await interaction.response.send_message("❌ Invalid egg type!", ephemeral=True)
            return
        if p.get("inventory", {}).get(egg_name, 0) < 1:
            await interaction.response.send_message(f"❌ You don't have a **{egg_name}** in your inventory!", ephemeral=True)
            return
        p["inventory"][egg_name] -= 1
        if p["inventory"][egg_name] <= 0:
            del p["inventory"][egg_name]
        if "pets" not in p:
            p["pets"] = []
        hatched_name = random.choice(["Starlight Fox", "Nebula Slime", "Cosmic Drake", "Astral Pup", "Void Cat"])
        p["pets"].append({"name": hatched_name, "level": 1, "type": egg_name})
        update_player(uid, p)
        await interaction.response.send_message(f"🥚 Pet Hatched! Out popped a brand new **{hatched_name}** ({egg_name.title()})!")

    @discord.app_commands.command(name="pets", description="View your active Starlight companion pets.")
    async def pets(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        user_pets = p.get("pets", [])
        embed = discord.Embed(title=f"🐾 {interaction.user.display_name}'s Pet Sanctuary", color=discord.Color.green())
        if not user_pets:
            embed.description = "You don't have any pets yet! Buy an egg from `/shop` page 2 and use `/hatch`."
        else:
            embed.description = "\n".join([f"• **{pet['name']}** (Level {pet['level']} - {pet['type'].title()})" for pet in user_pets])
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="petadventure", description="Send your companion pets on an adventure to gather loot and XP (Unlocked in Area 12+).")
    async def petadventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        if p.get("area", 1) < 12:
            await interaction.response.send_message("❌ Pet Adventures are locked until **Area 12**! Use `/area` to progress.", ephemeral=True)
            return
            
        user_pets = p.get("pets", [])
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets in your sanctuary! Buy an egg from `/shop` page 2 and use `/hatch`.", ephemeral=True)
            return

        pet = random.choice(user_pets)
        area = p.get("area", 1)
        
        found_coins = random.randint(200, 500) * area * pet["level"]
        found_xp = random.randint(100, 300) * area * pet["level"]
        
        p["wallet"] += found_coins
        p["xp"] += found_xp
        
        materials = ["wood", "fish", "iron_ore", "crops"]
        found_mat = random.choice(materials)
        mat_qty = random.randint(3, 8) * area
        
        p["inventory"][found_mat] = p["inventory"].get(found_mat, 0) + mat_qty
        
        level_msg = ""
        if random.random() < 0.35:
            pet["level"] += 1
            level_msg = f"\n🌟 **PET LEVEL UP!** Your **{pet['name']}** reached Level {pet['level']}!"

        level_up_char_msg = self._check_level_up(p)
        update_player(uid, p)

        embed = discord.Embed(title=f"🐾 Pet Expedition: {pet['name']}", description=f"Your loyal companion **{pet['name']}** (Level {pet['level']}) returned from a successful expedition into the wilderness!", color=discord.Color.green())
        embed.add_field(name="EXPEDITION SPOILS", value=f"🪙 Coins: +{found_coins:,}\n⭐ XP: +{found_xp:,}\n📦 Materials: +{mat_qty}x {found_mat.replace('_', ' ').title()}{level_msg}{level_up_char_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="inventory", description="Check your items, materials, and gear.")
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

    @discord.app_commands.command(name="chop", description="Chop wood in the forest for crafting materials.")
    async def chop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        wood = random.randint(2, 6) * p.get("area", 1)
        p["inventory"]["wood"] = p["inventory"].get("wood", 0) + wood
        self._update_quest_progress(p, "chop", wood)
        update_player(uid, p)
        await interaction.response.send_message(f"🪓 You swung your axe and collected **{wood}x Wood**!")

    @discord.app_commands.command(name="fish", description="Fish in the river for aquatic catches.")
    async def fish(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        fish_caught = random.randint(1, 4) * p.get("area", 1)
        p["inventory"]["fish"] = p["inventory"].get("fish", 0) + fish_caught
        self._update_quest_progress(p, "fish", fish_caught)
        update_player(uid, p)
        await interaction.response.send_message(f"🎣 You cast your line and caught **{fish_caught}x Fish**!")

    @discord.app_commands.command(name="mine", description="Mine ores in the caves (Unlocked in Area 5+).")
    async def mine(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if p.get("area", 1) < 5:
            await interaction.response.send_message("❌ Mining is locked until **Area 5**! Use `/area` to travel.", ephemeral=True)
            return
        ore = random.randint(2, 5) * p.get("area", 1)
        p["inventory"]["iron_ore"] = p["inventory"].get("iron_ore", 0) + ore
        self._update_quest_progress(p, "mine", ore)
        update_player(uid, p)
        await interaction.response.send_message(f"⛏️ You swung your pickaxe and mined **{ore}x Iron Ore**!")

    @discord.app_commands.command(name="farm", description="Farm crops in your garden (Unlocked in Area 4+).")
    async def farm(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if p.get("area", 1) < 4:
            await interaction.response.send_message("❌ Farming is locked until **Area 4**!", ephemeral=True)
            return
        if p.get("inventory", {}).get("seed", 0) < 1:
            await interaction.response.send_message("❌ You need a **seed** from `/shop` page 1 to farm!", ephemeral=True)
            return
        p["inventory"]["seed"] -= 1
        if p["inventory"]["seed"] <= 0:
            del p["inventory"]["seed"]
        crops = random.randint(5, 12) * p.get("area", 1)
        p["inventory"]["crops"] = p["inventory"].get("crops", 0) + crops
        update_player(uid, p)
        await interaction.response.send_message(f"🌱 You planted a seed and harvested **{crops}x Crops**!")

    @discord.app_commands.command(name="cook", description="Cook raw fish and ingredients into healing food (Area 5+).")
    async def cook(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if p.get("area", 1) < 5:
            await interaction.response.send_message("❌ Cooking is locked until **Area 5**!", ephemeral=True)
            return
        if p.get("inventory", {}).get("fish", 0) < 2:
            await interaction.response.send_message("❌ You need at least **2x Fish** in your inventory to cook!", ephemeral=True)
            return
        p["inventory"]["fish"] -= 2
        p["inventory"]["cooked_fish"] = p["inventory"].get("cooked_fish", 0) + 1
        update_player(uid, p)
        await interaction.response.send_message("🍳 You cooked your fish into a delicious **Cooked Fish** meal!")

    @discord.app_commands.command(name="coinflip", description="Flip a coin to double your bet or lose it all (Area 5+).")
    @discord.app_commands.describe(bet="Amount of coins to bet", choice="Choose heads or tails")
    @discord.app_commands.choices(choice=[
        discord.app_commands.Choice(name="Heads", value="heads"),
        discord.app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, bet: int, choice: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if p.get("area", 1) < 5:
            await interaction.response.send_message("❌ The Casino is locked until **Area 5**!", ephemeral=True)
            return
        if bet <= 0 or p["wallet"] < bet:
            await interaction.response.send_message(f"❌ Invalid bet! Your wallet has 🪙 {p['wallet']:,}.", ephemeral=True)
            return

        result = random.choice(["heads", "tails"])
        if choice == result:
            p["wallet"] += bet
            update_player(uid, p)
            await interaction.response.send_message(f"🪙 The coin landed on **{result.upper()}**! You won **🪙 {bet:,} coins**!")
        else:
            p["wallet"] -= bet
            update_player(uid, p)
            await interaction.response.send_message(f"❌ The coin landed on **{result.upper()}**. You lost your bet of 🪙 {bet:,} coins.")

    @discord.app_commands.command(name="multidice", description="Roll high-stakes dice against the bot in the casino (Area 5+).")
    @discord.app_commands.describe(bet="Amount of coins to bet")
    async def multidice(self, interaction: discord.Interaction, bet: int):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if p.get("area", 1) < 5:
            await interaction.response.send_message("❌ The Casino is locked until **Area 5**!", ephemeral=True)
            return
        if bet <= 0 or p["wallet"] < bet:
            await interaction.response.send_message(f"❌ Invalid bet! Your wallet has 🪙 {p['wallet']:,}.", ephemeral=True)
            return

        user_roll = random.randint(1, 6) + random.randint(1, 6)
        bot_roll = random.randint(1, 6) + random.randint(1, 6)

        if user_roll > bot_roll:
            p["wallet"] += bet
            outcome = f"🎉 You rolled **{user_roll}** vs Bot's **{bot_roll}**. You won **🪙 {bet:,} coins**!"
        elif user_roll < bot_roll:
            p["wallet"] -= bet
            outcome = f"😢 You rolled **{user_roll}** vs Bot's **{bot_roll}**. You lost **🪙 {bet:,} coins**."
        else:
            outcome = f"🤝 Both rolled **{user_roll}**! It's a tie, your bet was returned."

        update_player(uid, p)
        await interaction.response.send_message(f"🎲 **Casino Dice Table**\n{outcome}")

    @discord.app_commands.command(name="slots", description="Spin the Starlight Casino slot machine (Area 5+).")
    @discord.app_commands.describe(bet="Amount of coins to bet")
    async def slots(self, interaction: discord.Interaction, bet: int):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if p.get("area", 1) < 5:
            await interaction.response.send_message("❌ The Casino is locked until **Area 5**!", ephemeral=True)
            return
        if bet <= 0 or p["wallet"] < bet:
            await interaction.response.send_message(f"❌ Invalid bet! Your wallet has 🪙 {p['wallet']:,}.", ephemeral=True)
            return

        fruits = ["🍒", "🍋", "🍊", "🔔", "⭐", "💎"]
        spin = [random.choice(fruits) for _ in range(3)]
        slot_display = f"| {spin[0]} | {spin[1]} | {spin[2]} |"

        if spin[0] == spin[1] == spin[2]:
            multiplier = 10 if spin[0] == "💎" else 5
            winnings = bet * multiplier
            p["wallet"] += winnings
            msg = f"🎰 {slot_display}\n🎉 **JACKPOT!** Three {spin[0]}s! You won **🪙 {winnings:,} coins** ({multiplier}x)!"
        elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
            winnings = bet * 2
            p["wallet"] += winnings
            msg = f"🎰 {slot_display}\n✨ **Winner!** Two matching symbols! You won **🪙 {winnings:,} coins** (2x)!"
        else:
            p["wallet"] -= bet
            msg = f"🎰 {slot_display}\n😢 No match. You lost your bet of 🪙 {bet:,} coins."

        update_player(uid, p)
        await interaction.response.send_message(msg)

    @discord.app_commands.command(name="daily", description="Claim your daily rewards!")
    async def daily(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        bonus_coins = 500 * p.get("area", 1)
        p["wallet"] += bonus_coins
        update_player(uid, p)
        await interaction.response.send_message(f"🎁 You claimed your daily reward and received **🪙 {bonus_coins:,} coins**!")

    @discord.app_commands.command(name="heal", description="Heal your HP back to maximum.")
    async def heal(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        p["hp"] = p["max_hp"]
        update_player(uid, p)
        await interaction.response.send_message(f"❤️ You restored your HP to **{p['max_hp']}/{p['max_hp']}**!")

    @discord.app_commands.command(name="quest", description="Check your current active Starlight quest or take a new one.")
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

        embed = discord.Embed(title="📜 Active Starlight Quest", color=discord.Color.gold())
        embed.add_field(name=active["title"], value=f"*{active['desc']}*\n\n**Progress:** {active['progress']}/{active['target']}\n**Rewards:** 🪙 {active['reward_coins']:,} coins | ⭐ {active['reward_xp']:,} XP", inline=False)
        embed.set_footer(text="✨ Quest completed! Use /claimquest" if active["progress"] >= active["target"] else "🔒 Complete this quest before taking a new one.")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="claimquest", description="Claim your rewards for completing your active quest.")
    async def claimquest(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        active = p.get("active_quest")
        if not active or active["progress"] < active["target"]:
            await interaction.response.send_message("❌ You have no completed quest to claim right now!", ephemeral=True)
            return
        p["wallet"] += active["reward_coins"]
        p["xp"] += active["reward_xp"]
        p["active_quest"] = None
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"🎉 **Quest Completed!** Received 🪙 **{active['reward_coins']:,} coins** and ⭐ **{active['reward_xp']:,} XP**!{level_msg}")

async def setup(bot):
    await bot.add_cog(RpgCog(bot))
