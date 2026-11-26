import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player
from items import SWORDS, ARMORS, HORSES, MISC_ITEMS, PET_EGGS, BUNDLES, RESOURCES, PLUSHIES


def _truncate_field(text: str, limit: int = 1020) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 15].rsplit("\n", 1)[0] + "\n*...more in /shop*"


def build_master_catalog():
    """Builds a lowercase item lookup dictionary from all catalogs in items.py."""
    catalog = {}
    for s in SWORDS.values():
        catalog[s["name"].lower()] = s
    for a in ARMORS.values():
        catalog[a["name"].lower()] = a
    for h in HORSES.values():
        catalog[h["name"].lower()] = h
    for name, data in PET_EGGS.items():
        catalog[name.lower()] = {"price": data["price"]}
    for name, data in MISC_ITEMS.items():
        catalog[name.lower()] = {"price": data["price"]}
    for name, data in BUNDLES.items():
        catalog[name.lower()] = {"price": data["price"]}
    for name, data in RESOURCES.items():
        catalog[name.lower()] = {"price": data["price"]}
    for name, data in PLUSHIES.items():
        catalog[name.lower()] = {"price": data["price"]}
    return catalog


class ShopSelect(discord.ui.Select):
    def __init__(self, cog, user_id):
        self.cog = cog
        self.user_id = user_id
        options = [
            discord.SelectOption(label="Page 1: Weapons & Armor", value="1", emoji="⚔️", description="Tiers 1–15 Swords & Armor Sets"),
            discord.SelectOption(label="Page 2: Eggs & Utilities", value="2", emoji="🥚", description="Pet Eggs, Potions & Life Boosts"),
            discord.SelectOption(label="Page 3: Lootboxes & Bundles", value="3", emoji="📦", description="Mystery Crates & Starter Packs"),
            discord.SelectOption(label="Page 4: Crafting Resources", value="4", emoji="🪵", description="Wood, Ores & Rare Biome Materials"),
            discord.SelectOption(label="Page 5: Collectible Plushies", value="5", emoji="🧸", description="Classic & Teaser Plushies (Part 1)"),
            discord.SelectOption(label="Page 6: More Plushies", value="6", emoji="✨", description="Mythic & Flex Plushies (Part 2)"),
        ]
        super().__init__(placeholder="Select a shop category (Pages 1–6)...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        page = int(self.values[0])
        embed = self.cog.get_shop_embed(page)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ShopPaginationView(discord.ui.View):
    def __init__(self, cog, user_id, current_page=1):
        super().__init__(timeout=120)
        self.cog = cog
        self.user_id = user_id
        self.current_page = current_page
        self.add_item(ShopSelect(cog, user_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message("❌ You cannot control someone else's shop menu!", ephemeral=True)
            return False
        return True


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_shop_embed(self, page: int) -> discord.Embed:
        plush_items = list(PLUSHIES.items())
        midpoint = (len(plush_items) + 1) // 2

        if page == 1:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 1/6 (Weapons & Armor)", color=discord.Color.blue())
            swords_text = _truncate_field(
                "\n".join([f"⚔️ **{data['name']}** (T{tier}) | 🪙 {data['price']:,}" for tier, data in SWORDS.items()])
            )
            armors_text = _truncate_field(
                "\n".join([f"🛡️ **{data['name']}** (T{tier}) | 🪙 {data['price']:,}" for tier, data in ARMORS.items()])
            )
            embed.add_field(name="Swords (Tiers 1–15)", value=swords_text or "None", inline=True)
            embed.add_field(name="Armor Sets (Tiers 1–15)", value=armors_text or "None", inline=True)
        elif page == 2:
            embed = discord.Embed(title="🛒 Starlight Shop - Page 2/6 (Eggs & Utilities)", color=discord.Color.blue())
            eggs_text = _truncate_field(
                "\n".join([f"🥚 **{name}** | 🪙 {data['price']:,}\n*{data['desc']}*" for name, data in PET_EGGS.items()])
            )
            misc_text = _truncate_field(
                "\n".join([f"🧪 **{name}** | 🪙 {data['price']:,}\n*{data['desc']}*" for name, data in MISC_ITEMS.items() if "lootbox" not in name])
            )
            embed.add_field(name="Pet Eggs (Incl. Transcendent)", value=eggs_text or "None", inline=False)
            embed.add_field(name="Utilities, Consumables & Boosts", value=misc_text or "None", inline=False)
        elif page == 3:
            embed = discord.Embed(title="✨ Starlight Shop - Page 3/6 (Lootboxes & Bundles)", color=discord.Color.purple())
            lootboxes_text = _truncate_field(
                "\n".join([f"📦 **{name}** | 🪙 {data['price']:,}\n*{data['desc']}*" for name, data in MISC_ITEMS.items() if "lootbox" in name])
            )
            bundles_text = _truncate_field(
                "\n\n".join([f"🎁 **{b_name}** | 🪙 {data['price']:,}\n*Contents: {', '.join(data['contents'].keys())}*" for b_name, data in BUNDLES.items()])
            )
            embed.add_field(name="Lootboxes", value=lootboxes_text or "None", inline=False)
            embed.add_field(name="Starlight Bundles", value=bundles_text or "None", inline=False)
        elif page == 4:
            embed = discord.Embed(title="🪵 Starlight Shop - Page 4/6 (Crafting Resources)", color=discord.Color.green())
            res_text = _truncate_field(
                "\n".join([f"🧱 **{name}** | 🪙 {data['price']:,}\n*{data['desc']}*" for name, data in RESOURCES.items()])
            )
            embed.add_field(name="Raw Materials & Catalysts", value=res_text or "None", inline=False)
        elif page == 5:
            embed = discord.Embed(title="🧸 Starlight Shop - Page 5/6 (Collectible Plushies)", color=discord.Color.magenta())
            plush_text = _truncate_field(
                "\n".join([f"🧸 **{name}** | 🪙 {data['price']:,}\n*{data['desc']}*" for name, data in plush_items[:midpoint]])
            )
            embed.add_field(name="Hoarder's Plushie Collection (Part 1)", value=plush_text or "None", inline=False)
        else:
            embed = discord.Embed(title="🧸 Starlight Shop - Page 6/6 (More Plushies)", color=discord.Color.magenta())
            plush_text = _truncate_field(
                "\n".join([f"🧸 **{name}** | 🪙 {data['price']:,}\n*{data['desc']}*" for name, data in plush_items[midpoint:]])
            )
            embed.add_field(name="Hoarder's Plushie Collection (Part 2)", value=plush_text or "None", inline=False)

        embed.set_footer(text="Use /buy item_name:<name> quantity:<amount> to purchase! (Use /economy for wallet & bank)")
        return embed

    async def item_name_autocomplete(self, interaction: discord.Interaction, current: str):
        query = current.lower().strip()
        catalog = build_master_catalog()
        matches = [
            app_commands.Choice(name=name.title(), value=name)
            for name in catalog.keys()
            if not query or query in name
        ]
        return matches[:25]

    @app_commands.command(name="shop", description="View the Starlight Shop catalog.")
    async def shop(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        embed = self.get_shop_embed(1)
        view = ShopPaginationView(self, uid, 1)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="buy", description="Buy an item from the Starlight Shop catalog.")
    @app_commands.describe(item_name="Name of the item to buy", quantity="Quantity to purchase (default 1)")
    @app_commands.autocomplete(item_name=item_name_autocomplete)
    async def buy(self, interaction: discord.Interaction, item_name: str, quantity: int = 1):
        uid = str(interaction.user.id)
        p = get_player(uid)
        item_lower = item_name.lower().strip()

        if quantity < 1:
            await interaction.response.send_message("❌ Quantity must be at least 1!", ephemeral=True)
            return

        master_catalog = build_master_catalog()
        if item_lower not in master_catalog:
            await interaction.response.send_message(f"❌ Unknown item **'{item_name}'**! Check `/shop`.", ephemeral=True)
            return

        item_data = master_catalog[item_lower]
        item_price = item_data["price"]
        total_cost = item_price * quantity
        wallet = p.get("wallet", 0)
        if wallet < total_cost:
            await interaction.response.send_message(
                f"❌ You need **🪙 {total_cost:,}** coins, but your wallet has **🪙 {wallet:,}**.",
                ephemeral=True
            )
            return

        p["wallet"] = wallet - total_cost
        inv = p.setdefault("inventory", {})

        if any(item_lower == s["name"].lower() for s in SWORDS.values()):
            p["sword_origin"] = "shop"
        elif any(item_lower == a["name"].lower() for a in ARMORS.values()):
            p["armor_origin"] = "shop"

        inv[item_lower] = inv.get(item_lower, 0) + quantity
        update_player(uid, p)

        await interaction.response.send_message(
            f"🛒 Successfully purchased **{quantity}x {item_name.title()}** for **🪙 {total_cost:,} coins**!"
        )


async def setup(bot):
    await bot.add_cog(ShopCog(bot))
