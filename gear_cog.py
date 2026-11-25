import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player
from items import ARMORS, SWORDS


def get_owned_gear_tiers(player: dict, slot: str, current_tier: int) -> list[int]:
    """Return sorted gear tiers the player has owned/crafted, plus current_tier."""
    if not isinstance(player, dict):
        return [current_tier] if current_tier else []

    catalog = SWORDS if slot == "weapon" else ARMORS
    inv = player.get("inventory") if isinstance(player.get("inventory"), dict) else {}

    list_keys = (
        ["owned_swords", "crafted_swords", "unlocked_swords", "swords"]
        if slot == "weapon"
        else ["owned_armors", "crafted_armors", "unlocked_armors", "armors"]
    )
    max_keys = (
        ["max_sword_tier", "highest_sword_tier", "sword_tier"]
        if slot == "weapon"
        else ["max_armor_tier", "highest_armor_tier", "armor_tier"]
    )

    allowed = {int(current_tier)} if int(current_tier) in catalog else set()

    for key in list_keys:
        raw = player.get(key)
        if isinstance(raw, (list, tuple, set)):
            for entry in raw:
                if isinstance(entry, int) and entry in catalog:
                    allowed.add(entry)
                elif isinstance(entry, str) and entry.strip().isdigit():
                    tier_num = int(entry.strip())
                    if tier_num in catalog:
                        allowed.add(tier_num)
                elif isinstance(entry, dict) and isinstance(entry.get("tier"), int):
                    if entry["tier"] in catalog:
                        allowed.add(entry["tier"])
        elif isinstance(raw, dict):
            for k, v in raw.items():
                if v and str(k).isdigit() and int(k) in catalog:
                    allowed.add(int(k))

    for key in max_keys:
        val = player.get(key)
        if isinstance(val, int) and val >= 1:
            for t_num in range(1, min(val, max(catalog.keys())) + 1):
                if t_num in catalog:
                    allowed.add(t_num)

    for tier, data in catalog.items():
        item_name = str(data.get("name", "")).strip().lower()
        if item_name and int(inv.get(item_name, 0)) > 0:
            allowed.add(tier)

    return sorted(allowed)


class GearEquipSelect(discord.ui.Select):
    def __init__(self, user_id: str, slot: str, current_tier: int, allowed_tiers: list[int]):
        self.user_id = user_id
        self.slot = slot  # "weapon" or "armor"

        catalog = SWORDS if slot == "weapon" else ARMORS
        options = []

        for tier in allowed_tiers:
            data = catalog.get(tier)
            if not data:
                continue
            name = str(data.get("name", f"Tier {tier}")).title()
            stat_label = f"AT {data.get('at', tier)}" if slot == "weapon" else f"DEF {data.get('def', 0)}"
            is_equipped = tier == current_tier
            desc = f"Equipped • {stat_label}" if is_equipped else f"Unlocked • {stat_label}"
            options.append(
                discord.SelectOption(
                    label=f"T{tier}: {name}"[:100],
                    value=str(tier),
                    description=desc[:100],
                    emoji="✅" if is_equipped else ("⚔️" if slot == "weapon" else "🛡️"),
                    default=is_equipped,
                )
            )

        if not options:
            fallback_tier = current_tier if current_tier in catalog else 1
            data = catalog.get(fallback_tier, {})
            name = str(data.get("name", f"Tier {fallback_tier}")).title()
            options.append(
                discord.SelectOption(
                    label=f"T{fallback_tier}: {name}"[:100],
                    value=str(fallback_tier),
                    description="No extra unlocked tiers yet"[:100],
                    emoji="⚔️" if slot == "weapon" else "🛡️",
                    default=True,
                )
            )

        placeholder = (
            "Choose an unlocked sword/weapon to equip..."
            if slot == "weapon"
            else "Choose an unlocked armor to equip..."
        )
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options[:25],
            custom_id=f"gear_cog_select_{slot}",
        )

    async def callback(self, interaction: discord.Interaction):
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ This gear menu doesn't belong to you!",
                ephemeral=True,
            )
            return

        chosen_tier = int(self.values[0])
        player = get_player(self.user_id)
        if not isinstance(player, dict) or not player:
            await interaction.response.send_message("❌ No RPG profile found yet.", ephemeral=True)
            return

        tier_key = "sword_tier" if self.slot == "weapon" else "armor_tier"
        origin_key = "sword_origin" if self.slot == "weapon" else "armor_origin"
        catalog = SWORDS if self.slot == "weapon" else ARMORS

        current_tier = int(player.get(tier_key, 1))
        allowed_tiers = get_owned_gear_tiers(player, self.slot, current_tier)

        if chosen_tier not in allowed_tiers:
            gear_type = "sword/weapon" if self.slot == "weapon" else "armor"
            await interaction.response.send_message(
                f"❌ You haven't crafted or unlocked **Tier {chosen_tier}** {gear_type}!",
                ephemeral=True,
            )
            return

        data = catalog.get(chosen_tier)
        if not data:
            await interaction.response.send_message("❌ Invalid gear tier.", ephemeral=True)
            return

        origin = str(player.get(origin_key, "shop")).lower()
        player[tier_key] = chosen_tier
        player[origin_key] = origin
        update_player(self.user_id, player)

        if self.slot == "weapon":
            perk = " (+15% Hunt Coins)" if origin == "crafted" else ""
            msg = f"⚔️ Equipped **Tier {chosen_tier}: {data['name'].title()}** `[{origin.upper()}]`{perk}!"
        else:
            perk = " (+25% Gathering Yield)" if origin == "crafted" else ""
            msg = f"🛡️ Equipped **Tier {chosen_tier}: {data['name'].title()}** `[{origin.upper()}]`{perk}!"

        await interaction.response.edit_message(content=msg, view=None)


class GearEquipView(discord.ui.View):
    def __init__(self, user_id: str, slot: str, current_tier: int, allowed_tiers: list[int]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.add_item(GearEquipSelect(user_id, slot, current_tier, allowed_tiers))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ This gear menu doesn't belong to you!", ephemeral=True)
            return False
        return True


class GearCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="gear", description="Equip an unlocked or crafted sword or armor tier.")
    @app_commands.describe(slot="Choose whether to equip a weapon (sword) or armor")
    @app_commands.choices(
        slot=[
            app_commands.Choice(name="Sword / Weapon", value="weapon"),
            app_commands.Choice(name="Armor", value="armor"),
        ]
    )
    async def gear(self, interaction: discord.Interaction, slot: app_commands.Choice[str]):
        uid = str(interaction.user.id)
        player = get_player(uid)
        if not isinstance(player, dict) or not player:
            await interaction.response.send_message("❌ No RPG profile found yet.", ephemeral=True)
            return

        chosen_slot = slot.value
        tier_key = "sword_tier" if chosen_slot == "weapon" else "armor_tier"
        current_tier = int(player.get(tier_key, 1))
        allowed_tiers = get_owned_gear_tiers(player, chosen_slot, current_tier)

        view = GearEquipView(uid, chosen_slot, current_tier, allowed_tiers)
        prompt = (
            "⚔️ Select an unlocked/crafted sword or weapon to equip:"
            if chosen_slot == "weapon"
            else "🛡️ Select an unlocked/crafted armor to equip:"
        )
        await interaction.response.send_message(prompt, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GearCog(bot))
