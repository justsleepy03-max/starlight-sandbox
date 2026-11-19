import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, update_player

DATA_DIR = "/app/data"
GUILDS_FILE = os.path.join(DATA_DIR, "guilds.json")

os.makedirs(DATA_DIR, exist_ok=True)


def load_guilds_data():
    if not os.path.exists(GUILDS_FILE):
        return {"guilds": {}, "members": {}}
    try:
        with open(GUILDS_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"guilds": {}, "members": {}}
            data.setdefault("guilds", {})
            data.setdefault("members", {})
            return data
    except json.JSONDecodeError:
        return {"guilds": {}, "members": {}}


def save_guilds_data(data):
    with open(GUILDS_FILE, "w") as f:
        json.dump(data, f, indent=4)


class GuildsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="guild", description="View your guild details or browse available clans.")
    async def guild(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        data = load_guilds_data()
        members = data.get("members", {})
        guilds = data.get("guilds", {})

        guild_name = members.get(uid)

        if not guild_name or guild_name not in guilds:
            embed = discord.Embed(
                title="🏰 Starlight Guilds & Clans",
                description=(
                    "You are currently not a member of any guild!\n\n"
                    "Use **`/guildcreate <name>`** to found your own clan or ask a leader for an invite!"
                ),
                color=discord.Color.blurple()
            )
            return await interaction.response.send_message(embed=embed)

        g_data = guilds[guild_name]
        owner_id = str(g_data.get("owner_id", ""))
        owner_user = await self.bot.fetch_user(int(owner_id)) if owner_id.isdigit() else None
        owner_name = owner_user.name if owner_user else "Unknown Leader"

        guild_members = g_data.get("members", [])
        shown_mentions = []
        hidden_count = 0
        running_len = 0
        for m_id in guild_members:
            mention = f"<@!{m_id}>"
            extra = len(mention) + (2 if shown_mentions else 0)
            if running_len + extra > 950:
                hidden_count += 1
            else:
                shown_mentions.append(mention)
                running_len += extra

        member_display = ", ".join(shown_mentions) if shown_mentions else "None"
        if hidden_count > 0:
            member_display += f" *(+{hidden_count} more)*"

        embed = discord.Embed(
            title=f"🛡️ Guild: {guild_name}",
            description=g_data.get("motd", "Welcome to the guild! Work together to grow stronger."),
            color=discord.Color.gold()
        )
        embed.add_field(name="👑 Guild Master", value=owner_name, inline=True)
        embed.add_field(name="⭐ Guild Level", value=f"Level {g_data.get('level', 1)}", inline=True)
        embed.add_field(name="🏛️ Treasury", value=f"🪙 {g_data.get('treasury', 0):,} coins", inline=True)
        embed.add_field(
            name=f"👥 Members ({len(guild_members)})",
            value=member_display,
            inline=False
        )
        embed.set_footer(text="Use /guilddonate to contribute coins to your guild treasury!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guildcreate", description="Found your own guild for 50,000 coins.")
    @app_commands.describe(guild_name="Choose a unique name for your guild")
    async def guildcreate(self, interaction: discord.Interaction, guild_name: str):
        uid = str(interaction.user.id)
        clean_name = guild_name.strip()

        if len(clean_name) < 3 or len(clean_name) > 25:
            return await interaction.response.send_message(
                "❌ Guild names must be between 3 and 25 characters long!",
                ephemeral=True
            )

        data = load_guilds_data()
        members = data.setdefault("members", {})
        guilds = data.setdefault("guilds", {})

        if uid in members:
            return await interaction.response.send_message(
                "❌ You are already in a guild! Leave your current guild first.",
                ephemeral=True
            )

        if clean_name.lower() in [g.lower() for g in guilds]:
            return await interaction.response.send_message(
                "❌ A guild with that name already exists!",
                ephemeral=True
            )

        player_data = get_player(uid)
        wallet = player_data.get("wallet", 0)
        creation_cost = 50000

        if wallet < creation_cost:
            return await interaction.response.send_message(
                f"❌ Founding a guild requires **🪙 {creation_cost:,} coins**, "
                f"but your wallet only has **🪙 {wallet:,}**.",
                ephemeral=True
            )

        player_data["wallet"] = wallet - creation_cost
        update_player(uid, player_data)

        guilds[clean_name] = {
            "owner_id": uid,
            "treasury": 0,
            "level": 1,
            "motd": f"Welcome to {clean_name}!",
            "members": [uid]
        }
        members[uid] = clean_name
        save_guilds_data(data)

        embed = discord.Embed(
            title="🎉 Guild Founded Successfully!",
            description=(
                f"You are now the proud Founder and Guild Master of **{clean_name}**!\n\n"
                "Use `/guildinvite` to recruit members."
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guildinvite", description="Invite another player to join your guild.")
    @app_commands.describe(member="The user you want to invite")
    async def guildinvite(self, interaction: discord.Interaction, member: discord.Member):
        uid = str(interaction.user.id)
        target_id = str(member.id)
        data = load_guilds_data()
        members = data.setdefault("members", {})
        guilds = data.setdefault("guilds", {})

        guild_name = members.get(uid)
        if not guild_name or guild_name not in guilds:
            return await interaction.response.send_message("❌ You aren't in any guild!", ephemeral=True)

        guild_info = guilds[guild_name]
        if str(guild_info.get("owner_id", "")) != uid:
            return await interaction.response.send_message(
                "❌ Only the Guild Master can invite new members!",
                ephemeral=True
            )

        if target_id in members:
            return await interaction.response.send_message(
                "❌ That user is already in a guild!",
                ephemeral=True
            )

        guild_members = guild_info.setdefault("members", [])
        members[target_id] = guild_name
        if target_id not in guild_members:
            guild_members.append(target_id)
        save_guilds_data(data)

        await interaction.response.send_message(
            f"✅ Successfully invited {member.mention} to **{guild_name}**!"
        )

    @app_commands.command(name="guilddonate", description="Donate coins from your wallet into your guild treasury.")
    @app_commands.describe(amount="Amount of coins to donate")
    async def guilddonate(self, interaction: discord.Interaction, amount: int):
        uid = str(interaction.user.id)
        if amount <= 0:
            return await interaction.response.send_message(
                "❌ Donation amount must be greater than zero!",
                ephemeral=True
            )

        data = load_guilds_data()
        members = data.get("members", {})
        guilds = data.get("guilds", {})

        guild_name = members.get(uid)
        if not guild_name or guild_name not in guilds:
            return await interaction.response.send_message(
                "❌ You must be in a guild to donate!",
                ephemeral=True
            )

        player_data = get_player(uid)
        wallet = player_data.get("wallet", 0)
        if wallet < amount:
            return await interaction.response.send_message(
                f"❌ You don't have **🪙 {amount:,} coins** in your wallet!",
                ephemeral=True
            )

        player_data["wallet"] = wallet - amount
        update_player(uid, player_data)

        guild_info = guilds[guild_name]
        guild_info["treasury"] = guild_info.get("treasury", 0) + amount
        save_guilds_data(data)

        embed = discord.Embed(
            title="🏛️ Guild Treasury Contribution",
            description=(
                f"Successfully donated **🪙 {amount:,} coins** to **{guild_name}**!\n"
                f"Total Treasury: 🪙 {guild_info['treasury']:,}"
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guildleave", description="Leave your current guild.")
    async def guildleave(self, interaction: discord.Interaction):
        uid = str(interaction.user.id)
        data = load_guilds_data()
        members = data.setdefault("members", {})
        guilds = data.setdefault("guilds", {})

        guild_name = members.get(uid)
        if not guild_name or guild_name not in guilds:
            members.pop(uid, None)
            save_guilds_data(data)
            return await interaction.response.send_message(
                "❌ You are not currently in a guild!",
                ephemeral=True
            )

        guild_info = guilds[guild_name]
        guild_members = guild_info.setdefault("members", [])
        if uid in guild_members:
            guild_members.remove(uid)
        members.pop(uid, None)

        if not guild_members:
            guilds.pop(guild_name, None)
            msg = f"🏰 You left and disbanded **{guild_name}** as the last member."
        else:
            if str(guild_info.get("owner_id", "")) == uid:
                guild_info["owner_id"] = str(guild_members[0])
                msg = f"🏰 You left **{guild_name}**, and leadership transferred to <@!{guild_info['owner_id']}>."
            else:
                msg = f"🏰 You have left **{guild_name}**."

        save_guilds_data(data)
        await interaction.response.send_message(msg)


async def setup(bot):
    await bot.add_cog(GuildsCog(bot))
