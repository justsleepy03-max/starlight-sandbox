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
            return json.load(f)
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
                description="You are currently not a member of any guild!\n\nUse **`/guildcreate <name>`** to found your own clan or ask a leader for an invite!",
                color=discord.Color.blurple()
            )
            return await interaction.response.send_message(embed=embed)

        g_data = guilds[guild_name]
        owner_id = g_data["owner_id"]
        owner_user = await self.bot.fetch_user(int(owner_id)) if owner_id.isdigit() else None
        owner_name = owner_user.name if owner_user else "Unknown Leader"

        member_list = [f"<@!{m_id}>" for m_id in g_data["members"]]

        embed = discord.Embed(
            title=f"🛡️ Guild: {guild_name}",
            description=g_data.get("motd", "Welcome to the guild! Work together to grow stronger."),
            color=discord.Color.gold()
        )
        embed.add_field(name="👑 Guild Master", value=owner_name, inline=True)
        embed.add_field(name="⭐ Guild Level", value=f"Level {g_data.get('level', 1)}", inline=True)
        embed.add_field(name="🏛️ Treasury", value=f"🪙 {g_data.get('treasury', 0):,} coins", inline=True)
        embed.add_field(name=f"👥 Members ({len(g_data['members'])})", value=", ".join(member_list) if member_list else "None", inline=False)
        embed.set_footer(text="Use /guilddonate to contribute coins to your guild treasury!")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guildcreate", description="Found your own guild for 50,000 coins.")
    @app_commands.describe(guild_name="Choose a unique name for your guild")
    async def guildcreate(self, interaction: discord.Interaction, guild_name: str):
        uid = str(interaction.user.id)
        clean_name = guild_name.strip()

        if len(clean_name) < 3 or len(clean_name) > 25:
            return await interaction.response.send_message("❌ Guild names must be between 3 and 25 characters long!", ephemeral=True)

        data = load_guilds_data()
        if uid in data.get("members", {}):
            return await interaction.response.send_message("❌ You are already in a guild! Leave your current guild first.", ephemeral=True)

        if clean_name.lower() in [g.lower() for g in data.get("guilds", {})]:
            return await interaction.response.send_message("❌ A guild with that name already exists!", ephemeral=True)

        player_data = get_player(uid)
        creation_cost = 50000

        if player_data["wallet"] < creation_cost:
            return await interaction.response.send_message(f"❌ Founding a guild requires **🪙 {creation_cost:,} coins**, but your wallet only has **🪙 {player_data['wallet']:,}**.", ephemeral=True)

        player_data["wallet"] -= creation_cost
        update_player(uid, player_data)

        data.setdefault("guilds", {})[clean_name] = {
            "owner_id": uid,
            "treasury": 0,
            "level": 1,
            "motd": f"Welcome to {clean_name}!",
            "members": [uid]
        }
        data.setdefault("members", {})[uid] = clean_name
        save_guilds_data(data)

        embed = discord.Embed(
            title="🎉 Guild Founded Successfully!",
            description=f"You are now the proud Founder and Guild Master of **{clean_name}**!\n\nUse `/guildinvite` to recruit members.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="guildinvite", description="Invite another player to join your guild.")
    @app_commands.describe(member="The user you want to invite")
    async def guildinvite(self, interaction: discord.Interaction, member: discord.Member):
        uid = str(interaction.user.id)
        target_id = str(member.id)
        data = load_guilds_data()

        guild_name = data.get("members", {}).get(uid)
        if not guild_name:
            return await interaction.response.send_message("❌ You aren't in any guild!", ephemeral=True)

        guild_info = data["guilds"][guild_name]
        if guild_info["owner_id"] != uid:
            return await interaction.response.send_message("❌ Only the Guild Master can invite new members!", ephemeral=True)

        if target_id in data.get("members", {}):
            return await interaction.response.send_message("❌ That user is already in a guild!", ephemeral=True)

        data.setdefault("members", {})[target_id] = guild_name
        guild_info["members"].append(target_id)
        save_guilds_data(data)

        await interaction.response.send_message(f"✅ Successfully invited {member.mention} to **{guild_name}**!")

    @app_commands.command(name="guilddonate", description="Donate coins from your wallet into your guild treasury.")
    @app_commands.describe(amount="Amount of coins to donate")
    async def guilddonate(self, interaction: discord.Interaction, amount: int):
        uid = str(interaction.user.id)
        if amount <= 0:
            return await interaction.response.send_message("❌ Donation amount must be greater than zero!", ephemeral=True)

        data = load_guilds_data()
        guild_name = data.get("members", {}).get(uid)
        if not guild_name:
            return await interaction.response.send_message("❌ You must be in a guild to donate!", ephemeral=True)

        player_data = get_player(uid)
        if player_data["wallet"] < amount:
            return await interaction.response.send_message(f"❌ You don't have **🪙 {amount:,} coins** in your wallet!", ephemeral=True)

        player_data["wallet"] -= amount
        update_player(uid, player_data)

        guild_info = data["guilds"][guild_name]
        guild_info["treasury"] += amount
        save_guilds_data(data)

        embed = discord.Embed(
            title="🏛️ Guild Treasury Contribution",
            description=f"Successfully donated **🪙 {amount:,} coins** to **{guild_name}**!\nTotal Treasury: 🪙 {guild_info['treasury']:,}",
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(GuildsCog(bot))
