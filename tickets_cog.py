import os
import io
import json
import asyncio
from datetime import datetime, timezone
import discord
from discord.ext import commands
from discord import app_commands

DATA_DIR = "/app/data"
TRANSCRIPTS_DIR = os.path.join(DATA_DIR, "transcripts")
CONFIG_FILE = os.path.join(DATA_DIR, "ticket_config.json")


def load_ticket_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}


def save_ticket_config(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


async def generate_and_send_transcript(channel: discord.TextChannel, closed_by: discord.Member):
    """Compiles channel history into a .txt transcript, backs it up to disk, and posts to the log channel."""
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    now = datetime.now(timezone.utc)
    timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{channel.name}_{timestamp_str}.txt"
    filepath = os.path.join(TRANSCRIPTS_DIR, filename)

    lines = [
        "====================================================",
        "        STARLIGHT SANDBOX — TICKET TRANSCRIPT       ",
        "====================================================",
        f"Ticket Channel : #{channel.name} ({channel.id})",
        f"Topic / Reason : {channel.topic or 'No topic recorded'}",
        f"Closed By      : {closed_by} ({closed_by.id})",
        f"Closed At (UTC): {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "====================================================\n",
    ]

    message_count = 0
    async for msg in channel.history(limit=None, oldest_first=True):
        message_count += 1
        msg_time = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        content = msg.content if msg.content else ""

        if msg.embeds:
            embed_titles = [e.title for e in msg.embeds if e.title]
            if embed_titles:
                content += f" [Embed: {', '.join(embed_titles)}]"

        if msg.attachments:
            att_urls = ", ".join([a.url for a in msg.attachments])
            content += f" [Attachments: {att_urls}]"

        if not content.strip():
            content = "[No text content]"

        lines.append(f"[{msg_time}] {msg.author} ({msg.author.id}): {content}")

    lines.append("\n====================================================")
    lines.append(f"Total Messages Logged: {message_count}")
    lines.append("====================================================")

    transcript_text = "\n".join(lines)

    # Save backup copy to Railway volume
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(transcript_text)
    except Exception as e:
        print(f"Warning: Could not write local transcript backup: {e}")

    # Find configured log channel, or fall back to #ticket-logs / #transit-logs
    guild = channel.guild
    config = load_ticket_config()
    log_channel_id = config.get(str(guild.id), {}).get("log_channel_id")
    log_channel = guild.get_channel(int(log_channel_id)) if log_channel_id else None

    if not log_channel:
        log_channel = (
            discord.utils.get(guild.text_channels, name="ticket-logs")
            or discord.utils.get(guild.text_channels, name="transit-logs")
        )

    if log_channel:
        embed = discord.Embed(
            title="📑 Ticket Transcript & Transit Log",
            color=discord.Color.from_str("#F1C40F"),
            timestamp=now
        )
        embed.add_field(name="Ticket", value=f"`#{channel.name}`", inline=True)
        embed.add_field(name="Closed By", value=closed_by.mention, inline=True)
        embed.add_field(name="Messages Logged", value=str(message_count), inline=True)
        embed.add_field(name="Details", value=channel.topic or "No reason recorded", inline=False)
        embed.set_footer(text="Starlight Sandbox • Automated Transit Log")

        file_buffer = io.BytesIO(transcript_text.encode("utf-8"))
        discord_file = discord.File(fp=file_buffer, filename=filename)

        try:
            await log_channel.send(embed=embed, file=discord_file)
        except discord.Forbidden:
            print(f"Missing permissions to send transcript in #{log_channel.name}")


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
        # Disable the button immediately so it can't be clicked twice during logging
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("📑 Generating transcript and closing this ticket channel in **5 seconds**...")

        # Compile and dispatch transcript before channel deletion
        await generate_and_send_transcript(interaction.channel, interaction.user)

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

    category = discord.utils.get(guild.categories, name="Support Tickets")
    if not category:
        category = await guild.create_category("Support Tickets")

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        target_member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        opened_by: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
    }

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
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(CloseTicketView())

    @app_commands.command(name="setticketlogs", description="[Admin] Set the channel where closed ticket transcripts are sent")
    @app_commands.describe(channel="The staff log channel for ticket transcripts")
    @app_commands.default_permissions(administrator=True)
    async def setticketlogs(self, interaction: discord.Interaction, channel: discord.TextChannel):
        config = load_ticket_config()
        guild_id = str(interaction.guild.id)
        config.setdefault(guild_id, {})["log_channel_id"] = channel.id
        save_ticket_config(config)

        embed = discord.Embed(
            title="✅ Ticket Transit Logs Configured",
            description=f"All closed ticket transcripts will now be archived and posted to {channel.mention}.",
            color=discord.Color.from_str("#F1C40F")
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            color=discord.Color.from_str("#F1C40F")
        )
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("✅ Ticket panel posted!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(TicketsCog(bot))
