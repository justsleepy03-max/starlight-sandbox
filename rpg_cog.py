import discord
from discord.ext import commands
import random
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, MISC_ITEMS, PET_EGGS, BUNDLES

QUEST_POOL = [
    {"id": "hunt_monsters", "title": "Monster Slayer", "desc": "Hunt 5 times in the wild", "target": 5, "type": "hunt", "reward_coins": 1000, "reward_xp": 500},
    {"id": "gather_wood", "title": "Lumberjack Duty", "desc": "Collect 15 Wood", "target": 15, "type": "chop", "reward_coins": 800, "reward_xp": 400},
    {"id": "catch_fish", "title": "Master Angler", "desc": "Catch 10 Fish", "target": 10, "type": "fish", "reward_coins": 800, "reward_xp": 400},
]

AREA_UNLOCKS = {
    1: "Default: /hunt, /adventure, /chop, /fish, /shop, /inventory, /quest",
    2: "/enchant, /area, /training",
    3: "/axe, /net, /pickup",
    4: "/ladder, /guild, /farm",
    5: "/mine, /multidice, /cook",
    6: "/bowsaw, /boat, /pickaxe",
    7: "/refine, /big arena, /alchemy",
    8: "/tractor, /wheel",
    9: "/chainsaw, /bigboat",
    10: "/drill, /minintboss",
    11: "/time travel, /forge, /greenhouse",
    12: "/dynamite, /pets, /ultraining, /badge",
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
    @discord.app_commands.describe(category="Filter by category (general, rpg, crafting, pets)")
    async def help_command(self, interaction: discord.Interaction, category: str = None):
        category = category.lower() if category else None
        
        if category == "general":
            embed = discord.Embed(title="❓ Starlight Help - General & Economy", color=discord.Color.blue())
            embed.add_field(name="Economy & Stats", value="`/profile` - View your level, XP, and HP\n`/bal` - Check your wallet and bank balances\n`/deposit` - Deposit coins into your bank\n`/withdraw` - Withdraw coins to your wallet\n`/daily` - Claim your daily coin rewards\n`/shop` - Browse the 3-page shop catalog\n`/buy` - Purchase items, boxes, or bundles", inline=False)
        elif category == "rpg":
            embed = discord.Embed(title="❓ Starlight Help - RPG & Exploration", color=discord.Color.green())
            embed.add_field(name="Combat & Quests", value="`/hunt` - Hunt monsters for XP and coins\n`/adventure` - Embark on high-tier adventures\n`/area` - View area unlocks and travel\n`/quest` - Check or take active quests\n`/claimquest` - Claim completed quest rewards\n`/heal` - Restore your HP with potions", inline=False)
        elif category in ["crafting", "pets"]:
            embed = discord.Embed(title="❓ Starlight Help - Crafting & Pets", color=discord.Color.purple())
            embed.add_field(name="Gathering & Companions", value="`/chop` - Chop wood in the forest\n`/fish` - Fish in the river\n`/inventory` - Check your items and materials\n`/hatch` - Hatch purchased eggs into pets\n`/pets` - View your active companion sanctuary", inline=False)
        else:
            embed = discord.Embed(title="✨ Starlight RPG - Command Directory", color=discord.Color.gold())
            embed.description = "Here are all available command categories. Use `/help category:<name>` for specific lists!"
            embed.add_field(name="📂 Categories", value="• **general** (Profile, Bal, Deposit, Withdraw, Daily, Shop, Buy)\n• **rpg** (Hunt, Adventure, Area, Quest, Claimquest, Heal)\n• **crafting** (Chop, Fish, Inventory)\n• **pets** (Hatch, Pets)", inline=False)
            embed.set_footer(text="Starlight Sandbox • Built for Epic RPG 1:1 Parity")

        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="profile", description="Check your RPG character stats, level, and gear.")
    async def profile(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        
        embed = discord.Embed(title=f"✨ {interaction.user.display_name}'s Profile", color=discord.Color.blurple())
        embed.add_field(name="PROGRESS", value=f"**Level:** {p['level']} ({p['xp']}/{p['level'] * 250} XP)\n**Area:** {p['area']}", inline=False)
        embed.add_field(name="STATS", value=f"❤️ **HP:** {p['hp']}/{p['max_hp']}", inline=False)
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

    @discord.app_commands.command(name="area", description="View your current area, unlocks, or travel to a new area.")
    @discord.app_commands.describe(target_area="Area number to travel to")
    async def area(self, interaction: discord.Interaction, target_area: int = None):
        uid = str(interaction.user.id)
        p = get_player(uid)
        current_area = p.get("area", 1)

        if target_area is None:
            embed = discord.Embed(title=f"🗺️ Starlight Area Progression (Current: Area {current_area})", color=discord.Color.blue())
            lines = [f"**Area {a_num}** [{'✅ Current' if a_num == current_area else '✅ Unlocked' if a_num < current_area else '🔒 Locked'}]\n*🔓 {unlocks}*\n" for a_num, unlocks in AREA_UNLOCKS.items()]
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
        await interaction.response.send_message(f"🚀 Successfully traveled to **Area {target_area}**! New commands and scaling unlocked.")

    @discord.app_commands.command(name="hunt", description="Hunt for monsters to gain XP and coins based on your area.")
    async def hunt(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        
        earned_coins = random.randint(20, 45) * area
        earned_xp = random.randint(15, 30) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        self._update_quest_progress(p, "hunt", 1)
        
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        embed = discord.Embed(title=f"⚔️ Hunt Completed (Area {area})", description="You fought courageously and emerged victorious!", color=discord.Color.green())
        embed.add_field(name="REWARDS", value=f"🪙 Coins: +{earned_coins:,}\n⭐ XP: +{earned_xp:,}{level_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="adventure", description="Embark on an epic adventure in your current area!")
    async def adventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        area = p.get("area", 1)
        
        earned_coins = random.randint(80, 180) * area
        earned_xp = random.randint(60, 130) * area
        
        p["wallet"] += earned_coins
        p["xp"] += earned_xp
        
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        
        embed = discord.Embed(title=f"🗺️ Epic Adventure (Area {area})", description="You adventured deep into the wilderness and triumphed over a miniboss!", color=discord.Color.orange())
        embed.add_field(name="REWARDS", value=f"🪙 Coins: +{earned_coins:,}\n⭐ XP: +{earned_xp:,}{level_msg}", inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="shop", description="View the Starlight RPG shop catalog.")
    @discord.app_commands.describe(page="Shop page number (1, 2, or 3 for Starlight Bundles)")
    async def shop(self, interaction: discord.Interaction, page: int = 1):
        if page == 1:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 1/3 (Essentials)", color=discord.Color.blue())
            embed.description = "🌟 **STARLIGHT VENDOR:** Browse essential gear and supplies."
            items_text = (
                "🧪 **life potion** | 🪙 25\n"
                "🛡️ **basic armor** | 🪙 200\n"
                "⚔️ **basic sword** | 🪙 150\n"
                "🐎 **basic horse** | 🪙 500\n"
                "🔑 **dungeon key** | 🪙 5,000\n"
                "🎫 **lottery ticket** | 🪙 50\n"
                "🌱 **seed** | 🪙 4,000"
            )
            embed.add_field(name="Catalog", value=items_text, inline=False)
        elif page == 2:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 2/3 (Lootboxes & Eggs)", color=discord.Color.blue())
            embed.description = "🌟 **STARLIGHT VENDOR:** Companion eggs and boxes! Use `/hatch` after buying an egg."
            items_text = (
                "📦 **common lootbox** | 🪙 800\n📦 **uncommon lootbox** | 🪙 6,000\n"
                "📦 **rare lootbox** | 🪙 40,000\n📦 **epic lootbox** | 🪙 150,000\n\n"
                "🥚 **common egg** | 🪙 1,000\n🥚 **golden egg** | 🪙 15,000\n🥚 **celestial egg** | 🪙 75,000"
            )
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
            await interaction.response.send_message("❌ Invalid egg type! Choose from `common egg`, `golden egg`, or `celestial egg`.", ephemeral=True)
            return
            
        if p.get("inventory", {}).get(egg_name, 0) < 1:
            await interaction.response.send_message(f"❌ You don't have a **{egg_name}** in your inventory! Buy one from `/shop` page 2.", ephemeral=True)
            return
            
        p["inventory"][egg_name] -= 1
        if p["inventory"][egg_name] <= 0:
            del p["inventory"][egg_name]
            
        if "pets" not in p:
            p["pets"] = []
            
        pet_names = ["Starlight Fox", "Nebula Slime", "Cosmic Drake", "Astral Pup", "Void Cat"]
        hatched_name = random.choice(pet_names)
        new_pet = {"name": hatched_name, "level": 1, "type": egg_name}
        p["pets"].append(new_pet)
        update_player(uid, p)
        
        embed = discord.Embed(title="🥚 Pet Hatched Successfully!", description=f"The egg cracked open, and out popped a brand new **{hatched_name}** ({egg_name.title()})!", color=discord.Color.green())
        embed.set_footer(text="Use /pets to view your active companions in your sanctuary!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="pets", description="View your active Starlight companion pets.")
    async def pets(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        user_pets = p.get("pets", [])
        
        embed = discord.Embed(title=f"🐾 {interaction.user.display_name}'s Pet Sanctuary", color=discord.Color.green())
        if not user_pets:
            embed.description = "You don't have any pets yet! Buy an egg from `/shop` page 2 and use `/hatch`."
        else:
            pets_list = "\n".join([f"• **{pet['name']}** (Level {pet['level']} - {pet['type'].title()})" for pet in user_pets])
            embed.description = pets_list
            
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="inventory", description="Check your items, materials, and gear.")
    async def inventory(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})
        
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name}'s Inventory", color=discord.Color.gold())
        if not inv:
            embed.description = "Your inventory is empty! Use `/chop`, `/fish`, or visit the `/shop`."
        else:
            inv_text = "\n".join([f"• **{item.title()}**: {qty}" for item, qty in inv.items()])
            embed.description = inv_text
            
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="chop", description="Chop wood in the forest for crafting materials.")
    async def chop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        wood_gained = random.randint(2, 6) * p.get("area", 1)
        p["inventory"]["wood"] = p["inventory"].get("wood", 0) + wood_gained
        self._update_quest_progress(p, "chop", wood_gained)
        update_player(uid, p)
        await interaction.response.send_message(f"🪓 You swung your axe and collected **{wood_gained}x Wood**!")

    @discord.app_commands.command(name="fish", description="Fish in the river for aquatic catches.")
    async def fish(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        fish_gained = random.randint(1, 4) * p.get("area", 1)
        p["inventory"]["fish"] = p["inventory"].get("fish", 0) + fish_gained
        self._update_quest_progress(p, "fish", fish_gained)
        update_player(uid, p)
        await interaction.response.send_message(f"🎣 You cast your line and caught **{fish_gained}x Fish**!")

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
        await interaction.response.send_message(f"❤️ You used a healing potion and restored your HP to **{p['max_hp']}/{p['max_hp']}**!")

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
                "id": selected["id"],
                "title": selected["title"],
                "desc": selected["desc"],
                "type": selected["type"],
                "progress": 0,
                "target": selected["target"],
                "reward_coins": selected["reward_coins"] * area,
                "reward_xp": selected["reward_xp"] * area
            }
            update_player(uid, p)
            active = p["active_quest"]

        embed = discord.Embed(title="📜 Active Starlight Quest", color=discord.Color.gold())
        embed.add_field(
            name=active["title"], 
            value=f"*{active['desc']}*\n\n**Progress:** {active['progress']}/{active['target']}\n**Rewards:** 🪙 {active['reward_coins']:,} coins | ⭐ {active['reward_xp']:,} XP", 
            inline=False
        )
        if active["progress"] >= active["target"]:
            embed.set_footer(text="✨ Quest completed! Use /claimquest to collect your rewards!")
        else:
            embed.set_footer(text="🔒 Locked: Complete this quest before taking a new one.")
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
