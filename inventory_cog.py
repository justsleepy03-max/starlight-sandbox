import random
import discord
from discord import app_commands
from discord.ext import commands
import database
from database import get_player


def _persist_player(uid: str, player_data: dict):
  if hasattr(database, "save_player"):
    database.save_player(uid, player_data)
  elif hasattr(database, "update_player"):
    database.update_player(uid, player_data)
  elif hasattr(database, "save_data"):
    database.save_data()
  elif hasattr(database, "save_db"):
    database.save_db()


LOOTBOX_TABLES = {
    "common lootbox": {
        "coins": (150, 400),
        "rolls": 2,
        "pool": [
            ("wood", 5, 15, 35),
            ("ancient stone", 5, 15, 35),
            ("fish", 3, 10, 25),
            ("life potion", 1, 2, 20),
            ("sweet nectar", 2, 5, 15),
            ("common egg", 1, 1, 10),
        ],
    },
    "uncommon lootbox": {
        "coins": (450, 1100),
        "rolls": 2,
        "pool": [
            ("wood", 12, 28, 30),
            ("ancient stone", 12, 28, 30),
            ("river pearl", 4, 12, 25),
            ("sweet nectar", 5, 12, 25),
            ("life potion", 2, 4, 20),
            ("soft bark", 2, 6, 15),
            ("common egg", 1, 1, 15),
            ("uncommon egg", 1, 1, 8),
        ],
    },
    "rare lootbox": {
        "coins": (1200, 2800),
        "rolls": 3,
        "pool": [
            ("river pearl", 10, 25, 30),
            ("soft bark", 6, 15, 25),
            ("sweet nectar", 10, 22, 25),
            ("life potion", 3, 7, 20),
            ("uncommon egg", 1, 1, 15),
            ("rare egg", 1, 1, 8),
        ],
    },
    "epic lootbox": {
        "coins": (3000, 6500),
        "rolls": 3,
        "pool": [
            ("river pearl", 20, 45, 30),
            ("soft bark", 15, 30, 25),
            ("life potion", 6, 12, 25),
            ("rare egg", 1, 1, 15),
            ("epic egg", 1, 1, 8),
        ],
    },
    "legendary lootbox": {
        "coins": (7500, 15000),
        "rolls": 4,
        "pool": [
            ("river pearl", 40, 80, 30),
            ("life potion", 10, 20, 25),
            ("epic egg", 1, 1, 18),
            ("golden egg", 1, 1, 10),
        ],
    },
}


class InventoryView(discord.ui.View):

  def __init__(self, user_id: str, player_data: dict):
    super().__init__(timeout=180)
    self.user_id = user_id
    self.player_data = player_data
    self.current_category = "inventory"  # inventory, equipment, or stats
    self.update_components()

  def update_components(self):
    self.clear_items()

    inv_btn = discord.ui.Button(
        label="Items/Materials",
        style=(
            discord.ButtonStyle.primary
            if self.current_category == "inventory"
            else discord.ButtonStyle.secondary
        ),
    )
    inv_btn.callback = self.switch_to_inventory
    self.add_item(inv_btn)

    equip_btn = discord.ui.Button(
        label="Equipment",
        style=(
            discord.ButtonStyle.primary
            if self.current_category == "equipment"
            else discord.ButtonStyle.secondary
        ),
    )
    equip_btn.callback = self.switch_to_equipment
    self.add_item(equip_btn)

    stats_btn = discord.ui.Button(
        label="Stats & Wallet",
        style=(
            discord.ButtonStyle.primary
            if self.current_category == "stats"
            else discord.ButtonStyle.secondary
        ),
    )
    stats_btn.callback = self.switch_to_stats
    self.add_item(stats_btn)

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    if str(interaction.user.id) != self.user_id:
      await interaction.response.send_message(
          "❌ This isn't your inventory!", ephemeral=True
      )
      return False
    return True

  async def _refresh_and_edit(self, interaction: discord.Interaction, category: str):
    self.player_data = get_player(self.user_id)
    self.current_category = category
    self.update_components()
    await interaction.response.edit_message(
        embed=self.build_embed(), view=self
    )

  async def switch_to_inventory(self, interaction: discord.Interaction):
    await self._refresh_and_edit(interaction, "inventory")

  async def switch_to_equipment(self, interaction: discord.Interaction):
    await self._refresh_and_edit(interaction, "equipment")

  async def switch_to_stats(self, interaction: discord.Interaction):
    await self._refresh_and_edit(interaction, "stats")

  def build_embed(self):
    embed = discord.Embed(
        title="🎒 Starlight Inventory", color=discord.Color.blue()
    )

    if self.current_category == "inventory":
      embed.description = (
          "Here are the items, materials, and goods you currently carry:"
      )
      inventory = self.player_data.get("inventory", {})
      if not inventory:
        embed.add_field(
            name="Empty",
            value=(
                "Your inventory has no items yet. Go questing or gathering!"
            ),
            inline=False,
        )
      else:
        items_list = "\n".join(
            [f"• **{item.title()}**: {qty:,}" for item, qty in inventory.items()]
        )
        embed.add_field(name="Stored Goods", value=items_list, inline=False)

    elif self.current_category == "equipment":
      embed.description = "Your currently equipped gear loadout:"
      equipment = self.player_data.get("equipment", {})
      if equipment:
        for slot, item in equipment.items():
          display_item = str(item).title() if item else "None Equipped"
          embed.add_field(
              name=str(slot).capitalize(), value=display_item, inline=True
          )
      else:
        sword_tier = self.player_data.get("sword_tier", 1)
        armor_tier = self.player_data.get("armor_tier", 1)
        embed.add_field(
            name="⚔️ Sword Tier",
            value=f"Tier {sword_tier}",
            inline=True,
        )
        embed.add_field(
            name="🛡️ Armor Tier",
            value=f"Tier {armor_tier}",
            inline=True,
        )

    elif self.current_category == "stats":
      embed.description = "Your personal profile metrics and balances:"
      embed.add_field(
          name="💰 Wallet",
          value=f"{self.player_data.get('wallet', 0):,} coins",
          inline=True,
      )
      embed.add_field(
          name="🏦 Bank",
          value=f"{self.player_data.get('bank', 0):,} coins",
          inline=True,
      )
      embed.add_field(
          name="❤️ HP",
          value=(
              f"{self.player_data.get('hp', 100)} /"
              f" {self.player_data.get('max_hp', 100)}"
          ),
          inline=True,
      )
      embed.add_field(
          name="⭐ Level",
          value=(
              f"Level {self.player_data.get('level', 1)} (XP:"
              f" {self.player_data.get('xp', 0):,})"
          ),
          inline=True,
      )

    embed.set_footer(text=f"User ID: {self.user_id} • Use /economy for bank transfers")
    return embed


class InventoryCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @app_commands.command(
      name="bag", description="Open your interactive Starlight inventory."
  )
  async def bag(self, interaction: discord.Interaction):
    uid = str(interaction.user.id)
    player_data = get_player(uid)

    view = InventoryView(uid, player_data)
    embed = view.build_embed()
    await interaction.response.send_message(embed=embed, view=view)

  async def lootbox_autocomplete(
      self, interaction: discord.Interaction, current: str
  ) -> list[app_commands.Choice[str]]:
    uid = str(interaction.user.id)
    player_data = get_player(uid)
    inventory = player_data.get("inventory", {})

    choices = []
    for item_key, qty in inventory.items():
      if qty > 0 and "lootbox" in item_key.lower():
        if current.lower() in item_key.lower():
          choices.append(
              app_commands.Choice(
                  name=f"{item_key.title()} (x{qty})", value=item_key
              )
          )
    return choices[:25]

  @app_commands.command(
      name="open", description="Open a lootbox from your Starlight inventory."
  )
  @app_commands.describe(
      lootbox="Select the lootbox you want to open",
      amount="How many of this lootbox to open (default: 1)",
  )
  @app_commands.autocomplete(lootbox=lootbox_autocomplete)
  async def open_lootbox(
      self,
      interaction: discord.Interaction,
      lootbox: str,
      amount: app_commands.Range[int, 1, 25] = 1,
  ):
    uid = str(interaction.user.id)
    player_data = get_player(uid)
    inventory = player_data.setdefault("inventory", {})

    # Match item key case-insensitively in player's inventory
    matched_key = next(
        (k for k in inventory if k.lower() == lootbox.strip().lower()),
        None,
    )

    if not matched_key or inventory.get(matched_key, 0) <= 0:
      await interaction.response.send_message(
          f"❌ You don't have any **{lootbox.title()}** in your `/bag`!",
          ephemeral=True,
      )
      return

    owned_qty = inventory[matched_key]
    if amount > owned_qty:
      await interaction.response.send_message(
          f"❌ You only have **{owned_qty}x {matched_key.title()}**!",
          ephemeral=True,
      )
      return

    table_key = matched_key.lower()
    table = LOOTBOX_TABLES.get(table_key, LOOTBOX_TABLES["common lootbox"])

    # Deduct opened lootboxes
    if owned_qty - amount <= 0:
      del inventory[matched_key]
    else:
      inventory[matched_key] = owned_qty - amount

    # Roll rewards
    total_coins = 0
    gained_items: dict[str, int] = {}

    pool_items = [(i[0], i[1], i[2]) for i in table["pool"]]
    pool_weights = [i[3] for i in table["pool"]]

    for _ in range(amount):
      total_coins += random.randint(*table["coins"])
      chosen = random.choices(
          pool_items, weights=pool_weights, k=table["rolls"]
      )
      for item_name, min_qty, max_qty in chosen:
        qty_won = random.randint(min_qty, max_qty)
        gained_items[item_name] = gained_items.get(item_name, 0) + qty_won

    # Apply rewards to player_data
    player_data["wallet"] = player_data.get("wallet", 0) + total_coins
    for item_name, qty_won in gained_items.items():
      existing_item_key = next(
          (k for k in inventory if k.lower() == item_name.lower()),
          item_name,
      )
      inventory[existing_item_key] = (
          inventory.get(existing_item_key, 0) + qty_won
      )

    _persist_player(uid, player_data)

    reward_lines = [f"• 💰 **+{total_coins:,} Coins**"]
    for item_name, qty_won in gained_items.items():
      reward_lines.append(f"• 📦 **+{qty_won:,}x {item_name.title()}**")

    embed = discord.Embed(
        title=f"🎁 Opened {amount}x {matched_key.title()}!",
        description="\n".join(reward_lines),
        color=0x00F0FF,
    )
    remaining = inventory.get(matched_key, 0)
    embed.set_footer(
        text=f"Remaining {matched_key.title()}: {remaining:,} • Check /bag"
    )
    await interaction.response.send_message(embed=embed)


async def setup(bot):
  await bot.add_cog(InventoryCog(bot))
