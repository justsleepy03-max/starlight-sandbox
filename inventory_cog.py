import discord
from discord.ext import commands
from discord.ui import Button, View


class InventoryView(View):

  def __init__(self, user_id, player_data):
    super().__init__(timeout=180)
    self.user_id = user_id
    self.player_data = player_data
    self.current_category = "inventory"  # inventory, equipment, or stats
    self.update_components()

  def update_components(self):
    self.clear_items()

    inv_btn = Button(
        label="Items/Materials",
        style=(
            discord.ButtonStyle.primary
            if self.current_category == "inventory"
            else discord.ButtonStyle.secondary
        ),
    )
    inv_btn.callback = self.switch_to_inventory
    self.add_item(inv_btn)

    equip_btn = Button(
        label="Equipment",
        style=(
            discord.ButtonStyle.primary
            if self.current_category == "equipment"
            else discord.ButtonStyle.secondary
        ),
    )
    equip_btn.callback = self.switch_to_equipment
    self.add_item(equip_btn)

    stats_btn = Button(
        label="Stats & Wallet",
        style=(
            discord.ButtonStyle.primary
            if self.current_category == "stats"
            else discord.ButtonStyle.secondary
        ),
    )
    stats_btn.callback = self.switch_to_stats
    self.add_item(stats_btn)

  async def switch_to_inventory(self, interaction: discord.Interaction):
    if interaction.user.id != self.user_id:
      return await interaction.response.send_message(
          "This isn't your inventory!", ephemeral=True
      )
    self.current_category = "inventory"
    self.update_components()
    await interaction.response.edit_message(
        embed=self.build_embed(), view=self
    )

  async def switch_to_equipment(self, interaction: discord.Interaction):
    if interaction.user.id != self.user_id:
      return await interaction.response.send_message(
          "This isn't your inventory!", ephemeral=True
      )
    self.current_category = "equipment"
    self.update_components()
    await interaction.response.edit_message(
        embed=self.build_embed(), view=self
    )

  async def switch_to_stats(self, interaction: discord.Interaction):
    if interaction.user.id != self.user_id:
      return await interaction.response.send_message(
          "This isn't your inventory!", ephemeral=True
      )
    self.current_category = "stats"
    self.update_components()
    await interaction.response.edit_message(
        embed=self.build_embed(), view=self
    )

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
            value="Your inventory has no items yet. Go questing or gathering!",
            inline=False,
        )
      else:
        items_list = "\n".join(
            [f"• **{item}**: {qty}" for item, qty in inventory.items()]
        )
        embed.add_field(name="Stored Goods", value=items_list, inline=False)

    elif self.current_category == "equipment":
      embed.description = "Your currently equipped gear loadout:"
      equipment = self.player_data.get("equipment", {})
      for slot, item in equipment.items():
        display_item = item if item else "None Equipped"
        embed.add_field(
            name=slot.capitalize(), value=display_item, inline=True
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
          value=f"{self.player_data.get('hp', 100)} / {self.player_data.get('max_hp', 100)}",
          inline=True,
      )
      embed.add_field(
          name="⭐ Level",
          value=f"Level {self.player_data.get('level', 1)} (XP: {self.player_data.get('xp', 0)})",
          inline=True,
      )

    embed.set_footer(text=f"User ID: {self.user_id}")
    return embed


class InventoryCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot

  @commands.slash_command(
      name="inventory", description="Open your interactive Starlight inventory."
  )
  async def inventory(self, ctx: discord.ApplicationContext):
    from __main__ import get_player

    player_data = get_player(ctx.author.id)

    view = InventoryView(ctx.author.id, player_data)
    embed = view.build_embed()
    await ctx.respond(embed=embed, view=view)


def setup(bot):
  bot.add_cog(InventoryCog(bot))
