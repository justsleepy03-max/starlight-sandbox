import os
import json
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
            return json.load(f)
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

    def update_components(self):
        self.clear_items()
        market_data = load_market_data()
        listings = market_data.get("listings", {})

        if not listings:
            return

        # Add a select dropdown for active market listings
        options = []
        for listing_id, item in list(listings.items())[:25]:  # Discord limit of 25 options
            seller_name = item.get("seller_name", "Unknown")
            options.append(
                discord.SelectOption(
                    label=f"{item['qty']}x {item['item_name'].title()} — 🪙 {item['price']:,}",
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

    async def purchase_callback(self, interaction: discord.Interaction):
        buyer_uid = str(interaction.user.id)
        market_data = load_market_data()
        listings = market_data.get("listings", {})
        
        listing_id = interaction.data["values"][0]
        if listing_id not in listings:
            return await interaction.response.send_message("❌ This listing is no longer available!", ephemeral=True)

        listing = listings[listing_id]
        seller_uid = listing["seller_uid"]

        if buyer_uid == seller_uid:
            return await interaction.response.send_message("❌ You cannot purchase your own listing!", ephemeral=True)

        buyer_data = get_player(buyer_uid)
        total_price = listing["price"]

        if buyer_data["wallet"] < total_price:
            return await interaction.response.send_message(f"❌ You need **🪙 {total_price:,}** coins to buy this, but your wallet only has **🪙 {buyer_data['wallet']:,}**.", ephemeral=True)

        # Execute transaction (Escrow transfer)
        buyer_data["wallet"] -= total_price
        buyer_data.setdefault("inventory", {})
        item_name = listing["item_name"]
        qty = listing["qty"]
        buyer_data["inventory"][item_name] = buyer_data["inventory"].get(item_name, 0) + qty
        update_player(buyer_uid, buyer_data)

        # Pay seller (if online/exists in db)
        seller_data = get_player(seller_uid)
        seller_data["wallet"] += total_price
        update_player(seller_uid, seller_data)

        # Remove listing
        del listings[listing_id]
        save_market_data(market_data)

        embed = discord.Embed(
            title="🛒 Marketplace Purchase Successful!",
            description=f"You successfully purchased **{qty}x {item_name.title()}** from **{listing['seller_name']}** for **🪙 {total_price:,} coins**!",
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
            description="Browse items listed by other players across the realm. Buy securely using escrow protection!\n",
            color=discord.Color.blurple()
        )

        if not listings:
            embed.add_field(name="Active Listings", value="The marketplace is currently empty. Use `/sell` to list items!", inline=False)
            await interaction.response.send_message(embed=embed)
            return

        lines = []
        for l_id, item in list(listings.items())[:10]:
            lines.append(f"• **{item['qty']}x {item['item_name'].title()}** — 🪙 **{item['price']:,} coins** *(Seller: {item['seller_name']})*")

        embed.add_field(name="Active Listings", value="\n".join(lines), inline=False)
        embed.set_footer(text="Select an item from the dropdown below to purchase it!")

        view = MarketplaceView(uid)
        await interaction.response.send_message(embed=embed, view=view if listings else None)

    @app_commands.command(name="sell", description="List an item from your inventory onto the community marketplace.")
    @app_commands.describe(item_name="Name of the item in your bag", quantity="Amount to sell", price="Total price in coins")
    async def sell(self, interaction: discord.Interaction, item_name: str, quantity: int, price: int):
        uid = str(interaction.user.id)
        item_lower = item_name.lower().strip()

        if quantity <= 0 or price <= 0:
            return await interaction.response.send_message("❌ Quantity and price must be greater than zero!", ephemeral=True)

        player_data = get_player(uid)
        inv = player_data.get("inventory", {})

        if inv.get(item_lower, 0) < quantity:
            return await interaction.response.send_message(f"❌ You don't have **{quantity}x {item_name.title()}** in your bag! (You have {inv.get(item_lower, 0)}).", ephemeral=True)

        # Deduct items from player inventory (Escrow hold)
        inv[item_lower] -= quantity
        if inv[item_lower] <= 0:
            del inv[item_lower]
        update_player(uid, player_data)

        # Create marketplace listing
        market_data = load_market_data()
        listing_id = f"{uid}_{int(discord.utils.utcnow().timestamp())}"
        
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
            description=f"Successfully listed **{quantity}x {item_name.title()}** for **🪙 {price:,} coins**!",
            color=discord.Color.gold()
        )
        embed.set_footer(text="Use /market to view all active community listings.")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(MarketplaceCog(bot))
