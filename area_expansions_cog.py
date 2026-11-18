import random
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

class AreaExpansionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    def _verify_area(self, p, required_area):
        unlocked = p.get("unlocked_area", 1)
        current = p.get("area", 1)
        return unlocked >= required_area or current >= required_area

    # --- AREA 2 ---
    @discord.app_commands.command(name="enchant", description="Enhance your sword or armor stats using ancient stones and coins (Area 2+).")
    @app_commands.describe(gear_type="Choose whether to enchant your sword or armor")
    @app_commands.choices(gear_type=[
        app_commands.Choice(name="Sword", value="sword"),
        app_commands.Choice(name="Armor", value="armor")
    ])
    async def enchant(self, interaction: discord.Interaction, gear_type: str):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 2):
            await interaction.response.send_message("❌ Requires Area 2 (Crumbling Ruins) or higher!", ephemeral=True)
            return

        coin_cost = 1500
        stone_cost = 5
        inv = p.get("inventory", {})
        if p["wallet"] < coin_cost or inv.get("ancient stone", 0) < stone_cost:
            await interaction.response.send_message(f"❌ You need 🪙 {coin_cost:,} coins and {stone_cost}x Ancient Stone!", ephemeral=True)
            return

        p["wallet"] -= coin_cost
        inv["ancient stone"] -= stone_cost
        stat_key = f"{gear_type}_tier"
        p[stat_key] = p.get(stat_key, 1) + 1
        update_player(uid, p)
        await interaction.response.send_message(f"✨ Successfully enchanted your {gear_type} to Tier {p[stat_key]}!")

    @discord.app_commands.command(name="training", description="Undergo rigorous training to earn bonus XP (Area 2+).")
    async def training(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 2):
            await interaction.response.send_message("❌ Requires Area 2 or higher!", ephemeral=True)
            return
        earned_xp = random.randint(100, 250) * p.get("area", 1)
        p["xp"] += earned_xp
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"🏋️‍♂️ Training complete! Gained +⭐ {earned_xp:,} XP!{level_msg}")

    # --- AREA 3 ---
    @discord.app_commands.command(name="axe", description="Lumber specialized timber from Area 3.")
    async def axe(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 3):
            await interaction.response.send_message("❌ Requires Area 3 (Sunken Riverbank) or higher!", ephemeral=True)
            return
        wood = random.randint(5, 12)
        p["inventory"]["timber"] = p["inventory"].get("timber", 0) + wood
        update_player(uid, p)
        await interaction.response.send_message(f"🪓 Chopped **{wood}x Specialized Timber**!")

    @discord.app_commands.command(name="net", description="Cast a deep-water net to catch river rare fish.")
    async def net(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 3):
            await interaction.response.send_message("❌ Requires Area 3 or higher!", ephemeral=True)
            return
        catch = random.randint(3, 8)
        p["inventory"]["river pearl"] = p["inventory"].get("river pearl", 0) + catch
        update_player(uid, p)
        await interaction.response.send_message(f"🎣 Net catch successful! Collected **{catch}x River Pearl**!")

    @discord.app_commands.command(name="pickup", description="Scavenge the riverbanks for hidden treasures.")
    async def pickup(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 3):
            await interaction.response.send_message("❌ Requires Area 3 or higher!", ephemeral=True)
            return
        coins = random.randint(100, 400)
        p["wallet"] += coins
        update_player(uid, p)
        await interaction.response.send_message(f"🔍 Scavenged riverbanks and found 🪙 {coins:,} coins!")

    # --- AREA 4 ---
    @discord.app_commands.command(name="ladder", description="Climb high ledges in the meadows for rare flora.")
    async def ladder(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 4):
            await interaction.response.send_message("❌ Requires Area 4 (Glimmering Meadows) or higher!", ephemeral=True)
            return
        p["inventory"]["sweet nectar"] = p["inventory"].get("sweet nectar", 0) + 3
        update_player(uid, p)
        await interaction.response.send_message("🪜 Climbed the ridge and gathered **3x Sweet Nectar**!")

    @discord.app_commands.command(name="farm", description="Harvest crops from your meadow plot.")
    async def farm(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 4):
            await interaction.response.send_message("❌ Requires Area 4 or higher!", ephemeral=True)
            return
        p["wallet"] += 750
        update_player(uid, p)
        await interaction.response.send_message("🌾 Harvested farm crops for 🪙 750 coins!")

    # --- AREA 5 ---
    @discord.app_commands.command(name="multidice", description="Roll high-stakes multi-dice for massive coin payouts.")
    async def multidice(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 5):
            await interaction.response.send_message("❌ Requires Area 5 (Crystal Caverns) or higher!", ephemeral=True)
            return
        roll = random.randint(1, 12)
        payout = roll * 200
        p["wallet"] += payout
        update_player(uid, p)
        await interaction.response.send_message(f"🎲 Rolled a **{roll}** on multi-dice! Won 🪙 {payout:,} coins!")

    @discord.app_commands.command(name="cook", description="Cook cave rations to restore health and boost stats.")
    async def cook(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 5):
            await interaction.response.send_message("❌ Requires Area 5 or higher!", ephemeral=True)
            return
        p["hp"] = min(p["max_hp"], p["hp"] + 50)
        update_player(uid, p)
        await interaction.response.send_message("🍲 Cooked a warm meal! Restored HP up to current max.")

    @discord.app_commands.command(name="casino", description="Test your luck at the crystal casino high tables.")
    async def casino(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 5):
            await interaction.response.send_message("❌ Requires Area 5 or higher!", ephemeral=True)
            return
        if random.random() > 0.5:
            win = 2000
            p["wallet"] += win
            await interaction.response.send_message(f"🎰 Jacked the casino slot! Won 🪙 {win:,} coins!")
        else:
            loss = 1000
            p["wallet"] = max(0, p["wallet"] - loss)
            await interaction.response.send_message(f"🎰 House wins! Lost 🪙 {loss:,} coins.")
        update_player(uid, p)

    # --- AREA 6 ---
    @discord.app_commands.command(name="bowsaw", description="Cut dense branches in the shadowed thicket.")
    async def bowsaw(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 6):
            await interaction.response.send_message("❌ Requires Area 6 (Shadowed Thicket) or higher!", ephemeral=True)
            return
        p["inventory"]["shadow petal"] = p["inventory"].get("shadow petal", 0) + 4
        update_player(uid, p)
        await interaction.response.send_message("🪚 Harvested **4x Shadow Petals** with a bowsaw!")

    @discord.app_commands.command(name="boat", description="Navigate dark thicket waters.")
    async def boat(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 6):
            await interaction.response.send_message("❌ Requires Area 6 or higher!", ephemeral=True)
            return
        p["xp"] += 300
        update_player(uid, p)
        await interaction.response.send_message("⛵ Sailed dark waters and gained +⭐ 300 XP!")

    @discord.app_commands.command(name="pickaxe", description="Heavy-duty pickaxe mining for dark mineral ore.")
    async def pickaxe(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 6):
            await interaction.response.send_message("❌ Requires Area 6 or higher!", ephemeral=True)
            return
        p["inventory"]["dark ore"] = p["inventory"].get("dark ore", 0) + 5
        update_player(uid, p)
        await interaction.response.send_message("⛏️ Extracted **5x Dark Ore**!")

    # --- AREA 7 ---
    @discord.app_commands.command(name="refine", description="Refine raw volcanic ores into pure magma blocks.")
    async def refine(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 7):
            await interaction.response.send_message("❌ Requires Area 7 (Volcanic Caldera) or higher!", ephemeral=True)
            return
        p["inventory"]["magma core"] = p["inventory"].get("magma core", 0) + 2
        update_player(uid, p)
        await interaction.response.send_message("🔥 Refined raw materials into **2x Magma Cores**!")

    @discord.app_commands.command(name="big_arena", description="Enter the high-intensity volcanic arena combat tournament.")
    async def big_arena(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 7):
            await interaction.response.send_message("❌ Requires Area 7 or higher!", ephemeral=True)
            return
        p["wallet"] += 5000
        p["xp"] += 1000
        update_player(uid, p)
        await interaction.response.send_message("🏟️ Triumphed in the Big Arena! Earned 🪙 5,000 coins & +⭐ 1,000 XP!")

    @discord.app_commands.command(name="alchemy", description="Brew volatile chemical mixtures from volcanic extracts.")
    async def alchemy(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 7):
            await interaction.response.send_message("❌ Requires Area 7 or higher!", ephemeral=True)
            return
        p["max_hp"] += 10
        update_player(uid, p)
        await interaction.response.send_message("⚗️ Brewed an elixir! Permanent Max HP increased by +10!")

    # --- AREA 8 ---
    @discord.app_commands.command(name="tractor", description="Farm large windplain fields efficiently.")
    async def tractor(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 8):
            await interaction.response.send_message("❌ Requires Area 8 (Whispering Windplains) or higher!", ephemeral=True)
            return
        p["wallet"] += 3000
        update_player(uid, p)
        await interaction.response.send_message("🚜 Tractor farming yielded 🪙 3,000 coins!")

    @discord.app_commands.command(name="wheel", description="Spin the windplain fortune wheel.")
    async def wheel(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 8):
            await interaction.response.send_message("❌ Requires Area 8 or higher!", ephemeral=True)
            return
        reward = random.choice([1000, 2500, 5000, 10000])
        p["wallet"] += reward
        update_player(uid, p)
        await interaction.response.send_message(f"🎡 Spun the wheel and won 🪙 {reward:,} coins!")

    # --- AREA 9 ---
    @discord.app_commands.command(name="chainsaw", description="Cut frozen timber in the sub-zero tundra.")
    async def chainsaw(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 9):
            await interaction.response.send_message("❌ Requires Area 9 (Frozen Tundra) or higher!", ephemeral=True)
            return
        p["inventory"]["everfrost ice"] = p["inventory"].get("everfrost ice", 0) + 5
        update_player(uid, p)
        await interaction.response.send_message("⚙️ Chainsawed **5x Everfrost Ice** blocks!")

    @discord.app_commands.command(name="bigboat", description="Break through icy straits with a heavy icebreaker vessel.")
    async def bigboat(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 9):
            await interaction.response.send_message("❌ Requires Area 9 or higher!", ephemeral=True)
            return
        p["xp"] += 2000
        update_player(uid, p)
        await interaction.response.send_message("🚢 Navigated frozen straits for +⭐ 2,000 XP!")

    # --- AREA 10 ---
    @discord.app_commands.command(name="drill", description="Industrial drill excavation into dragon spires.")
    async def drill(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 10):
            await interaction.response.send_message("❌ Requires Area 10 (Dragon's Spire) or higher!", ephemeral=True)
            return
        p["inventory"]["dragon scale"] = p["inventory"].get("dragon scale", 0) + 2
        update_player(uid, p)
        await interaction.response.send_message("🛠️ Drilled deep and retrieved **2x Dragon Scales**!")

    @discord.app_commands.command(name="minintboss", description="Challenge a mini-boss guarding the spire peak.")
    async def minintboss(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 10):
            await interaction.response.send_message("❌ Requires Area 10 or higher!", ephemeral=True)
            return
        p["wallet"] += 15000
        p["xp"] += 5000
        update_player(uid, p)
        await interaction.response.send_message("🐉 Defeated the spire mini-boss! Claimed 🪙 15,000 coins & +⭐ 5,000 XP!")

    # --- AREA 11 ---
    @discord.app_commands.command(name="time_travel", description="Slip through temporal anomalies to gather chrono dust.")
    async def time_travel(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 11):
            await interaction.response.send_message("❌ Requires Area 11 (Temporal Rift) or higher!", ephemeral=True)
            return
        p["inventory"]["chrono dust"] = p["inventory"].get("chrono dust", 0) + 3
        update_player(uid, p)
        await interaction.response.send_message("⏳ Traveled through time and secured **3x Chrono Dust**!")

    @discord.app_commands.command(name="temporal_forge", description="Forge temporal weapons across dimensions.")
    async def temporal_forge(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 11):
            await interaction.response.send_message("❌ Requires Area 11 or higher!", ephemeral=True)
            return
        p["sword_tier"] += 1
        update_player(uid, p)
        await interaction.response.send_message("⚔️ Forged temporal weapon! Sword tier increased by +1!")

    @discord.app_commands.command(name="greenhouse", description="Cultivate anomalous rift plants.")
    async def greenhouse(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 11):
            await interaction.response.send_message("❌ Requires Area 11 or higher!", ephemeral=True)
            return
        p["wallet"] += 8000
        update_player(uid, p)
        await interaction.response.send_message("🌿 Harvested greenhouse rift flora for 🪙 8,000 coins!")

    # --- AREA 12 ---
    @discord.app_commands.command(name="dynamite", description="Blast open celestial vault deposits.")
    async def dynamite(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 12):
            await interaction.response.send_message("❌ Requires Area 12 (Celestial Sanctuary) or higher!", ephemeral=True)
            return
        p["inventory"]["starlight essence"] = p["inventory"].get("starlight essence", 0) + 5
        update_player(uid, p)
        await interaction.response.send_message("🧨 Detonated vault and looted **5x Starlight Essence**!")

    @discord.app_commands.command(name="pets", description="Manage and view your celestial companions.")
    async def pets(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 12):
            await interaction.response.send_message("❌ Requires Area 12 or higher!", ephemeral=True)
            return
        await interaction.response.send_message("🐾 Sanctuary Pet management interface opened successfully.")

    @discord.app_commands.command(name="petadventure", description="Send your companions on autonomous sanctuary adventures.")
    async def petadventure(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 12):
            await interaction.response.send_message("❌ Requires Area 12 or higher!", ephemeral=True)
            return
        p["wallet"] += 10000
        update_player(uid, p)
        await interaction.response.send_message("🗺️ Your pet returned from its adventure with 🪙 10,000 coins!")

    @discord.app_commands.command(name="ultraining", description="Push past mortal limits with ultra training.")
    async def ultraining(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 12):
            await interaction.response.send_message("❌ Requires Area 12 or higher!", ephemeral=True)
            return
        p["xp"] += 10000
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"⚡ Ultra training session yielded +⭐ 10,000 XP!{level_msg}")

    @discord.app_commands.command(name="badge", description="Inspect your hard-earned mastery badges.")
    async def badge(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 12):
            await interaction.response.send_message("❌ Requires Area 12 or higher!", ephemeral=True)
            return
        await interaction.response.send_message("🏅 Displaying high-tier mastery badges of the sanctuary.")

    # --- AREA 13 ---
    @discord.app_commands.command(name="transmute", description="Transmute base elements into abyssal void matter.")
    async def transmute(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 13):
            await interaction.response.send_message("❌ Requires Area 13 (Abyssal Depths) or higher!", ephemeral=True)
            return
        p["inventory"]["void matter"] = p["inventory"].get("void matter", 0) + 1
        update_player(uid, p)
        await interaction.response.send_message("🔮 Transmuted elements into **1x Void Matter**!")

    @discord.app_commands.command(name="hunt_hardmode", description="Venture into high-risk abyss monster hunts.")
    async def hunt_hardmode(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 13):
            await interaction.response.send_message("❌ Requires Area 13 or higher!", ephemeral=True)
            return
        p["wallet"] += 25000
        p["xp"] += 15000
        update_player(uid, p)
        await interaction.response.send_message("⚔️ Survived Abyssal Hardmode Hunt! Earned 🪙 25,000 coins & +⭐ 15,000 XP!")

    # --- AREA 14 ---
    @discord.app_commands.command(name="adventure_hardmode", description="Traverse mythical overgrowth wilderness on hardmode.")
    async def adventure_hardmode(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 14):
            await interaction.response.send_message("❌ Requires Area 14 (Mythic Overgrowth) or higher!", ephemeral=True)
            return
        p["inventory"]["world-tree sap"] = p["inventory"].get("world-tree sap", 0) + 2
        p["wallet"] += 40000
        update_player(uid, p)
        await interaction.response.send_message("🌲 Conquered Overgrowth Hardmode! Secured **2x World-Tree Sap** & 🪙 40,000 coins!")

    @discord.app_commands.command(name="big_dice", description="Roll cosmic dice for extreme financial rewards.")
    async def big_dice(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 14):
            await interaction.response.send_message("❌ Requires Area 14 or higher!", ephemeral=True)
            return
        roll = random.randint(1, 100)
        payout = roll * 1000
        p["wallet"] += payout
        update_player(uid, p)
        await interaction.response.send_message(f"🎯 Rolled **{roll}** with Big Dice! Won 🪙 {payout:,} coins!")

    # --- AREA 15 ---
    @discord.app_commands.command(name="time_jump", description="Perform a full dimensional time jump.")
    async def time_jump(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 15):
            await interaction.response.send_message("❌ Requires Area 15 (The Transcendence Core) or higher!", ephemeral=True)
            return
        p["xp"] += 50000
        level_msg = self._check_level_up(p)
        update_player(uid, p)
        await interaction.response.send_message(f"🌌 Executed time jump! Gained +⭐ 50,000 XP!{level_msg}")

    @discord.app_commands.command(name="transcend", description="Reach absolute transcendence at the core.")
    async def transcend(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        if not self._verify_area(p, 15):
            await interaction.response.send_message("❌ Requires Area 15 (The Transcendence Core) to transcend!", ephemeral=True)
            return
        p["wallet"] += 500000
        update_player(uid, p)
        await interaction.response.send_message("✨ **TRANSCENDENCE ACHIEVED!** You have conquered the Starlight engine and claimed 🪙 500,000 coins!")

async def setup(bot):
    await bot.add_cog(AreaExpansionsCog(bot))
