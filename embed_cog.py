import discord
from discord import app_commands
from discord.ext import commands


class EmbedModal(discord.ui.Modal, title="Starlight Interactive Embed Builder"):
    embed_title = discord.ui.TextInput(
        label="Embed Title (Optional)",
        placeholder="Optional title for your announcement/update...",
        required=False,
        max_length=256
    )

    embed_description = discord.ui.TextInput(
        label="Embed Description",
        placeholder="Enter the main body text (supports markdown)...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )

    embed_color = discord.ui.TextInput(
        label="Hex Color Code (Optional)",
        placeholder="Default: #F1C40F (Starlight Gold)",
        required=False,
        max_length=7
    )

    embed_footer = discord.ui.TextInput(
        label="Footer Text (Optional)",
        placeholder="e.g. Starlight Sandbox • Patch 4",
        required=False,
        max_length=2048
    )

    embed_ping = discord.ui.TextInput(
        label="Ping / Mention Above Embed (Optional)",
        placeholder="Type @everyone, @here, or <@&RoleID> to notify",
        required=False,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Default to Starlight Gold (#F1C40F) unless a custom hex is provided
        color = discord.Color.from_str("#F1C40F")
        if self.embed_color.value and self.embed_color.value.strip():
            clean_color = self.embed_color.value.strip().lstrip("#")
            try:
                color = discord.Color(int(clean_color, 16))
            except ValueError:
                pass

        clean_title = self.embed_title.value.strip() if self.embed_title.value else ""
        clean_description = self.embed_description.value.strip() if self.embed_description.value else ""

        # Build the embed, omitting title when left blank
        embed_kwargs = {
            "description": clean_description,
            "color": color
        }
        if clean_title:
            embed_kwargs["title"] = clean_title

        embed = discord.Embed(**embed_kwargs)

        if self.embed_footer.value and self.embed_footer.value.strip():
            embed.set_footer(text=self.embed_footer.value.strip())

        if interaction.guild:
            embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

        # Handle ping outside the embed so Discord triggers real notifications
        ping_content = self.embed_ping.value.strip() if self.embed_ping.value else None
        allowed_mentions = discord.AllowedMentions(everyone=True, roles=True, users=True)

        await interaction.channel.send(
            content=ping_content,
            embed=embed,
            allowed_mentions=allowed_mentions
        )
        await interaction.response.send_message("✅ Embed successfully built and sent!", ephemeral=True)


class EmbedCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="embedbuilder", description="Open the interactive modal to create and send a custom embed.")
    @app_commands.default_permissions(administrator=True)
    async def embedbuilder(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EmbedModal())


async def setup(bot):
    await bot.add_cog(EmbedCog(bot))
