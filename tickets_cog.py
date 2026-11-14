import discord
from discord.ext import commands
from discord import app_commands
import asyncio

# --- MODAL FOR MEMBER REASON INPUT ---
class TicketReasonModal(discord.ui.Modal, title="Open a Support Ticket"):
    reason = discord.ui.TextInput(
        label="What do you need help with?",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your issue, report, or question...",
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(
            interaction=interaction,
            target_member=interaction.user,
            opened_by=interaction.user,
            reason=self.reason.value,
            staff_initiated=False
        )

# --- PERSISTENT CLOSE BUTTON VIEW ---
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id="starlight:close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Closing and deleting this ticket channel in **5 seconds**...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to delete this channel.", ephemeral=True)

# --- PERSISTENT OPEN TICKET PANEL VIEW ---
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Open Support Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎟️",
        custom_id="starlight:open_ticket"
    )
    async def open_ticket_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketReasonModal())

# --- SHARED CHANNEL CREATION HELPER ---
async def create_ticket_channel(
    interaction: discord.Interaction,
    target_member: discord.Member,
    opened_by: discord.Member,
    reason: str,
    staff_initiated: bool
):
    guild = interaction.guild
    if not guild:
        return

    # Find or create a "Support Tickets" category
    category = discord.utils.get(guild.categories, name="Support Tickets")
    if not category:
        category = await guild.create_category("Support Tickets")

    # Set strict permissions: deny @everyone, allow target member, opener, bot, and manage_channels staff
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        target_member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        opened_by: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

    # Give any role with Manage Messages / Manage Channels access to support tickets
    for role in guild.roles:
        if role.permissions.manage_messages or role.permissions.administrator:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True)

    channel_name = f"ticket-{target_member.name}".lower()[:30]
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        category=category,
        overwrites=overwrites,
        topic=f"Support ticket for {target_member} | Reason: {reason}"
    )

    if staff_initiated:
        header_line = f"🎟️ **Private Support Ticket Opened by:** Staff Member ({opened_by.mention})\n**Member:** {target_member.mention}\n**Reason:** {reason}"
    else:
        header_line = f"🎟️ **Support Ticket Opened by:** {opened_by.mention}\n**Reason:** {reason}"

    embed = discord.Embed(
        title="Support Ticket",
        description=f"{header_line}\n\nThis is a secure, private channel between staff and the member. No DMs required!",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Click the button below when this issue is resolved.")

    await ticket_channel.send(
        content=f"{target_member.mention} {opened_by.mention if opened_by != target_member else ''}",
        embed=embed,
        view=CloseTicketView()
    )

    await interaction.response.send_message(
        f"✅ Ticket created: {ticket_channel.mention}",
        ephemeral=True
    )

# --- TICKETS COG ---
class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Register persistent views so buttons keep working after bot restarts
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(CloseTicketView())

    @app_commands.command(name="openticket", description="[Staff] Open a private support channel with a server member")
    @app_commands.describe(member="The member to open a private channel with", reason="Reason for opening the ticket")
    @app_commands.default_permissions(manage_messages=True)
    async def openticket(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Staff outreach"):
        if member.bot:
            return await interaction.response.send_message("❌ You cannot open a ticket with a bot.", ephemeral=True)
        await create_ticket_channel(
            interaction=interaction,
            target_member=member,
            opened_by=interaction.user,
            reason=reason,
            staff_initiated=True
        )

    @app_commands.command(name="ticketpanel", description="[Admin] Post the permanent member support ticket panel")
    @app_commands.default_permissions(administrator=True)
    async def ticketpanel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎟️ RVG Support & Inquiries",
            description=(
                "Need help from staff, want to report an issue, or have a private question?\n\n"
                "Click the **Open Support Ticket** button below to spin up a private channel with the staff team—no DMs required!"
            ),
            color=discord.Color.gold()
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("✅ Ticket panel posted!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
