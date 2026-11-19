import discord
from discord import app_commands
from discord.ext import commands
from database import get_player


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


async def setup(bot):
  await bot.add_cog(InventoryCog(bot))
