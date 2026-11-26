import json
from pathlib import Path
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

# Replace with your Discord User ID (int) if you want an explicit hard lock
EXPLICIT_OWNER_ID: Optional[int] = None

BUNDLES_FILE = Path("data/bundles.json")

DEFAULT_BUNDLES: dict[str, dict] = {
    "quest_fix": {
        "label": "Quest Bug Compensation",
        "coins": 15000,
        "xp": 6000,
        "items": {"magma core": 15},
        "eggs": {"common": 1},
    },
    "starter_boost": {
        "label": "Starter Supply Pack",
        "coins": 5000,
        "xp": 1500,
        "items": {"wood": 50, "iron ore": 25},
        "eggs": {"common": 1},
    },
    "tester_pack": {
        "label": "Playtester Compensation Pack",
        "coins": 25000,
        "xp": 10000,
        "items": {"wood": 100, "iron ore": 50, "magma core": 10},
        "eggs": {"golden": 1},
    },
}


def load_bundles() -> dict[str, dict]:
    if not BUNDLES_FILE.exists():
        BUNDLES_FILE.parent.mkdir(parents=True, exist_ok=True)
        save_bundles(DEFAULT_BUNDLES)
        return json.loads(json.dumps(DEFAULT_BUNDLES))
    with BUNDLES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_bundles(data: dict[str, dict]) -> None:
    BUNDLES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with BUNDLES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


class BundleAdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bundles: dict[str, dict] = load_bundles()

    async def _is_bot_owner(self, interaction: discord.Interaction) -> bool:
        if EXPLICIT_OWNER_ID is not None:
            return interaction.user.id == EXPLICIT_OWNER_ID
        if self.bot.owner_id is not None:
            return interaction.user.id == self.bot.owner_id
        if self.bot.application and self.bot.application.owner:
            return interaction.user.id == self.bot.application.owner.id
        return await self.bot.is_owner(interaction.user)

    async def _deny_non_owner(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "❌ Only the bot owner can use this command.",
            ephemeral=True,
        )

    def _apply_rewards(
        self,
        p: dict,
        coins: int = 0,
        xp: int = 0,
        items: Optional[dict[str, int]] = None,
        eggs: Optional[dict[str, int]] = None,
    ) -> list[str]:
        granted: list[str] = []

        if coins:
            p["wallet"] = int(p.get("wallet", 0)) + coins
            granted.append(f"🪙 **+{coins:,} Coins**")

        if xp:
            p["xp"] = int(p.get("xp", 0)) + xp
            granted.append(f"⭐ **+{xp:,} XP**")

        if items:
            inv = p.setdefault("inventory", {})
            for mat_name, qty in items.items():
                key = mat_name.strip().lower()
                if qty > 0:
                    inv[key] = int(inv.get(key, 0)) + int(qty)
                    granted.append(f"📦 **+{int(qty):,}x {key.title()}**")

        if eggs:
            egg_bag = p.setdefault("eggs", {})
            for rarity, qty in eggs.items():
                r_key = rarity.strip().lower()
                if qty > 0:
                    egg_bag[r_key] = int(egg_bag.get(r_key, 0)) + int(qty)
                    granted.append(f"🥚 **+{int(qty):,}x {r_key.title()} Egg**")

        return granted

    @app_commands.command(name="givebundle", description="[Owner Only] Send a bundle or custom bug-fix rewards to a player.")
    @app_commands.describe(
        member="Player to receive the bundle",
        bundle="Preset bundle name (optional if giving custom rewards)",
        coins="Extra/custom coins to grant",
        xp="Extra/custom XP to grant",
        item="Material/item name to grant (e.g., magma core)",
        item_qty="Quantity of the item to grant",
        egg_type="Egg rarity to grant (e.g., common, golden)",
        egg_qty="Number of eggs to grant",
    )
    async def givebundle(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        bundle: Optional[str] = None,
        coins: int = 0,
        xp: int = 0,
        item: Optional[str] = None,
        item_qty: int = 0,
        egg_type: Optional[str] = None,
        egg_qty: int = 0,
    ):
        if not await self._is_bot_owner(interaction):
            await self._deny_non_owner(interaction)
            return

        uid = str(member.id)
        p = get_player(uid)
        if not isinstance(p, dict) or not p:
            await interaction.response.send_message(
                f"❌ {member.mention} doesn't have an active RPG profile yet.",
                ephemeral=True,
            )
            return

        preset = self.bundles.get(bundle.lower()) if bundle else None
        if bundle and not preset:
            available = ", ".join(f"`{k}`" for k in self.bundles.keys()) or "*none*"
            await interaction.response.send_message(
                f"❌ Unknown bundle `{bundle}`. Available presets: {available}",
                ephemeral=True,
            )
            return

        total_coins = (preset.get("coins", 0) if preset else 0) + coins
        total_xp = (preset.get("xp", 0) if preset else 0) + xp

        merged_items: dict[str, int] = {}
        if preset and isinstance(preset.get("items"), dict):
            for k, v in preset["items"].items():
                merged_items[k.lower()] = merged_items.get(k.lower(), 0) + int(v)
        if item and item_qty > 0:
            i_key = item.strip().lower()
            merged_items[i_key] = merged_items.get(i_key, 0) + int(item_qty)

        merged_eggs: dict[str, int] = {}
        if preset and isinstance(preset.get("eggs"), dict):
            for k, v in preset["eggs"].items():
                merged_eggs[k.lower()] = merged_eggs.get(k.lower(), 0) + int(v)
        if egg_type and egg_qty > 0:
            e_key = egg_type.strip().lower()
            merged_eggs[e_key] = merged_eggs.get(e_key, 0) + int(egg_qty)

        granted = self._apply_rewards(
            p,
            coins=total_coins,
            xp=total_xp,
            items=merged_items,
            eggs=merged_eggs,
        )

        if not granted:
            await interaction.response.send_message(
                "❌ Nothing to send—choose a preset bundle or enter coins, XP, items, or eggs.",
                ephemeral=True,
            )
            return

        update_player(uid, p)

        title_label = preset["label"] if preset else "Custom Compensation Bundle"
        embed = discord.Embed(
            title=f"🎁 {title_label}",
            description=f"Sent to {member.mention} by {interaction.user.mention}:\n" + "\n".join(granted),
            color=discord.Color.gold(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setbundle", description="[Owner Only] Create or edit a bundle preset.")
    @app_commands.describe(
        name="Bundle key (e.g., quest_fix)",
        coins="Coins in this bundle",
        xp="XP in this bundle",
        item="Material/item name (optional)",
        item_qty="Quantity of that item",
        egg_type="Egg rarity (optional, e.g., common, golden)",
        egg_qty="Number of eggs",
        label="Display title for the bundle",
    )
    async def setbundle(
        self,
        interaction: discord.Interaction,
        name: str,
        coins: int = 0,
        xp: int = 0,
        item: Optional[str] = None,
        item_qty: int = 0,
        egg_type: Optional[str] = None,
        egg_qty: int = 0,
        label: Optional[str] = None,
    ):
        if not await self._is_bot_owner(interaction):
            await self._deny_non_owner(interaction)
            return

        key = name.strip().lower().replace(" ", "_")
        existing = self.bundles.get(key, {
            "label": key.replace("_", " ").title(),
            "coins": 0,
            "xp": 0,
            "items": {},
            "eggs": {},
        })

        existing["label"] = label.strip() if label else existing.get("label", key.replace("_", " ").title())
        existing["coins"] = max(0, coins)
        existing["xp"] = max(0, xp)

        items_dict: dict[str, int] = dict(existing.get("items") or {})
        if item:
            i_key = item.strip().lower()
            if item_qty > 0:
                items_dict[i_key] = int(item_qty)
            else:
                items_dict.pop(i_key, None)
        existing["items"] = items_dict

        eggs_dict: dict[str, int] = dict(existing.get("eggs") or {})
        if egg_type:
            e_key = egg_type.strip().lower()
            if egg_qty > 0:
                eggs_dict[e_key] = int(egg_qty)
            else:
                eggs_dict.pop(e_key, None)
        existing["eggs"] = eggs_dict

        self.bundles[key] = existing
        save_bundles(self.bundles)

        await interaction.response.send_message(
            f"✅ Saved bundle **`{key}`** (*{existing['label']}*) — "
            f"🪙 `{existing['coins']:,}` | ⭐ `{existing['xp']:,}` | "
            f"Items: `{existing['items']}` | Eggs: `{existing['eggs']}`",
            ephemeral=True,
        )

    @app_commands.command(name="listbundles", description="[Owner Only] View all configured bundle presets.")
    async def listbundles(self, interaction: discord.Interaction):
        if not await self._is_bot_owner(interaction):
            await self._deny_non_owner(interaction)
            return

        if not self.bundles:
            await interaction.response.send_message("No bundles configured yet.", ephemeral=True)
            return

        embed = discord.Embed(title="📦 Configured Bundles", color=discord.Color.blurple())
        for key, b in self.bundles.items():
            embed.add_field(
                name=f"`{key}` — {b.get('label', key)}",
                value=(
                    f"🪙 Coins: `{b.get('coins', 0):,}` • ⭐ XP: `{b.get('xp', 0):,}`\n"
                    f"📦 Items: `{b.get('items', {})}`\n"
                    f"🥚 Eggs: `{b.get('eggs', {})}`"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @givebundle.autocomplete("bundle")
    async def bundle_autocomplete(self, interaction: discord.Interaction, current: str):
        query = current.lower()
        return [
            app_commands.Choice(name=f"{k} ({v.get('label', k)})", value=k)
            for k, v in self.bundles.items()
            if query in k.lower() or query in str(v.get("label", "")).lower()
        ][:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(BundleAdminCog(bot))
