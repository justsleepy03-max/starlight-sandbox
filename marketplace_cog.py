import os
import json
import uuid
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
MARKET_FILE = os.path.join(DATA_DIR, "marketplace.json")

os.makedirs(DATA_DIR, exist_ok=True)


def load_market_data():
    if not os.path.exists(MARKET_FILE):
        return {"listings": {}}
    try:
        with open(MARKET_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"listings": {}}
            data.setdefault("listings", {})
            return data
    except json.JSONDecodeError:
        return {"listings": {}}


def save_market_data(data):
    with open(MARKET_FILE, "w") as f:
        json.dump(data, f, indent=4)


class MarketplaceView(discord.ui.View):
    def __init__(self, user_id: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.update_components()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if str(interaction.user.id) != self.user_id:
            await interaction.response.send_message(
                "❌ Open your own marketplace view with `/market`!",
                ephemeral=True
            )
            return False
        return True

    def update_components(self):
        self.clear_items()
        market_data = load_market_data()
        listings = market_data.setdefault("listings", {})

        if not listings:
            return

        options = []
        for listing_id, item in list(listings.items())[:25]:
            seller_name = item.get("seller_name", "Unknown")
            qty = item.get("qty", 1)
            price = item.get("price", 0)
            item_name = str(item.get("item_name", "item"))
            options.append(
                discord.SelectOption(
                    label=f"{qty:,}x {item_name.title()} — 🪙 {price:,}"[:100],
                    value=listing_id,
                    description=f"Seller: {seller_name}"[:100]
                )
            )

        select = discord.ui.Select(
            placeholder="Select a listing to purchase...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="market:buy_select"
        )
        select.callback = self.purchase_callback
        self.add_item(select)

        has_own_listing = any(
            str(item.get("seller_uid")) == self.user_id
            for item in listings.values()
        )
        if has_own_listing:
            cancel_btn = discord.ui.Button(
                label="Cancel My Oldest Listing",
                style=discord.ButtonStyle.danger
            )
            cancel_btn.callback = self.cancel_own_listing
            self.add_item(cancel_btn)

    async def cancel_own_listing(self, interaction: discord.Interaction):
        market_data = load_market_data()
        listings = market_data.setdefault("listings", {})

        target_id = None
        target_item = None
        for listing_id, item in listings.items():
            if str(item.get("seller_uid")) == self.user_id:
                target_id = listing_id
                target_item = item
                break

        if not target_id or not target_item:
            return await interaction.response.send_message(
                "❌ You don't have an active listing to cancel.",
                ephemeral=True
            )

        item_name = str(target_item.get("item_name", "")).lower().strip()
        qty = int(target_item.get("qty", 0))

        seller_data = get_player(self.user_id)
        inv = seller_data.setdefault("inventory", {})
        if item_name and qty > 0:
            inv[item_name] = inv.get(item_name, 0) + qty
            update_player(self.user_id, seller_data)

        listings.pop(target_id, None)
        save_market_data(market_data)

        await interaction.response.send_message(
            f"↩️ Cancelled your listing for **{qty:,}x {item_name.title()}** and returned it to your inventory!",
            ephemeral=True
        )

    async def purchase_callback(self, interaction: discord.Interaction):
        buyer_uid = str(interaction.user.id)
        market_data = load_market_data()
        listings = market_data.setdefault("listings", {})

        listing_id = interaction.data["values"][0]
        if listing_id not in listings:
            return await interaction.response.send_message(
                "❌ This listing is no longer available!",
                ephemeral=True
            )

        listing = listings[listing_id]
        seller_uid = str(listing.get("seller_uid", ""))

        if buyer_uid == seller_uid:
            return await interaction.response.send_message(
                "❌ You cannot purchase your own listing!",
                ephemeral=True
            )

        buyer_data = get_player(buyer_uid)
        buyer_wallet = buyer_data.get("wallet", 0)
        total_price = int(listing.get("price", 0))

        if buyer_wallet < total_price:
            return await interaction.response.send_message(
                f"❌ You need **🪙 {total_price:,}** coins to buy this, but your wallet only has **🪙 {buyer_wallet:,}**.",
                ephemeral=True
            )

        # Execute transaction (Escrow transfer)
        buyer_data["wallet"] = buyer_wallet - total_price
        buyer_inv = buyer_data.setdefault("inventory", {})
        item_name = str(listing.get("item_name", "item"))
        qty = int(listing.get("qty", 1))
        buyer_inv[item_name] = buyer_inv.get(item_name, 0) + qty
        update_player(buyer_uid, buyer_data)

        # Pay seller
        seller_data = get_player(seller_uid)
        seller_data["wallet"] = seller_data.get("wallet", 0) + total_price
        update_player(seller_uid, seller_data)

        # Remove listing
        listings.pop(listing_id, None)
        save_market_data(market_data)

        seller_name = listing.get("seller_name", "Unknown")
        embed = discord.Embed(
            title="🛒 Marketplace Purchase Successful!",
            description=(
                f"You successfully purchased **{qty:,}x {item_name.title()}** from "
                f"**{seller_name}** for **🪙 {total_price:,} coins**!"
            ),
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class MarketplaceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="market", description="Browse player-to-player marketplace listings.")
    async def market(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        market_data = load_market_data()
        listings = market_data.get("listings", {})

        embed = discord.Embed(
            title="✨ Starlight Community Marketplace",
            description=(
                "Browse items listed by other players across the realm. "
                "Buy securely using escrow protection!\n"
            ),
            color=discord.Color.blurple()
        )

        if not listings:
            embed.add_field(
                name="Active Listings",
                value="The marketplace is currently empty. Use `/sell` to list items!",
                inline=False
            )
            await interaction.response.send_message(embed=embed)
            return

        lines = []
        for item in list(listings.values())[:10]:
            item_name = str(item.get("item_name", "item"))
            qty = int(item.get("qty", 1))
            price = int(item.get("price", 0))
            seller_name = item.get("seller_name", "Unknown")
            lines.append(
                f"• **{qty:,}x {item_name.title()}** — 🪙 **{price:,} coins** "
                f"*(Seller: {seller_name})*"
            )

        embed.add_field(name="Active Listings", value="\n".join(lines), inline=False)
        embed.set_footer(text="Select an item from the dropdown below to purchase it!")

        view = MarketplaceView(uid)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="sell", description="List an item from your inventory onto the community marketplace.")
    @app_commands.describe(
        item_name="Name of the item in your bag",
        quantity="Amount to sell",
        price="Total price in coins"
    )
    async def sell(self, interaction: discord.Interaction, item_name: str, quantity: int, price: int):
        uid = str(interaction.user.id)
        item_lower = item_name.lower().strip()

        if not item_lower:
            return await interaction.response.send_message("❌ Please enter a valid item name!", ephemeral=True)

        if quantity <= 0 or price <= 0:
            return await interaction.response.send_message(
                "❌ Quantity and price must be greater than zero!",
                ephemeral=True
            )

        player_data = get_player(uid)
        inv = player_data.setdefault("inventory", {})
        owned_qty = inv.get(item_lower, 0)

        if owned_qty < quantity:
            return await interaction.response.send_message(
                f"❌ You don't have **{quantity:,}x {item_name.title()}** in your bag! "
                f"(You have {owned_qty:,}).",
                ephemeral=True
            )

        # Deduct items from player inventory (Escrow hold)
        inv[item_lower] = owned_qty - quantity
        if inv[item_lower] <= 0:
            inv.pop(item_lower, None)
        update_player(uid, player_data)

        # Create marketplace listing
        market_data = load_market_data()
        listing_id = f"{uid}_{int(discord.utils.utcnow().timestamp())}_{uuid.uuid4().hex[:6]}"

        market_data.setdefault("listings", {})[listing_id] = {
            "seller_uid": uid,
            "seller_name": interaction.user.display_name,
            "item_name": item_lower,
            "qty": quantity,
            "price": price
        }
        save_market_data(market_data)

        embed = discord.Embed(
            title="📦 Item Listed on Marketplace",
            description=(
                f"Successfully listed **{quantity:,}x {item_name.title()}** "
                f"for **🪙 {price:,} coins**!"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Use /market to view all active community listings.")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(MarketplaceCog(bot))
