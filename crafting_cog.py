@app_commands.command(name="materials", description="List crafting material pools, biome sources, and your current stock.")
    async def materials(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        p = get_player(uid)
        inv = p.get("inventory", {})

        embed = discord.Embed(
            title="🧪 Starlight Crafting Materials List",
            description="Rarity pools and how much you currently hold in your inventory:",
            color=discord.Color.teal(),
        )

        for pool_name, pool_items in MATERIAL_POOLS.items():
            lines = []
            for mat in pool_items:
                owned = inv.get(mat, 0)
                lines.append(f"`{mat}` *(x{owned:,})*")
            embed.add_field(
                name=pool_name,
                value=", ".join(lines),
                inline=False,
            )

        embed.set_footer(text="Use /recipes to see exact tier costs • Use /craft to forge")
        await interaction.response.send_message(embed=embed)
