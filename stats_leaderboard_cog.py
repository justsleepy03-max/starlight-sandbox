import discord
from discord import app_commands
from discord.ext import commands
from database import get_player, get_all_players


def _extract_weapon_text(p: dict) -> str:
    equip = p.get("equipment")
    if isinstance(equip, dict):
        weapon = equip.get("weapon") or equip.get("sword")
        if isinstance(weapon, dict):
            w_name = weapon.get("name") or "Weapon"
            w_tier = weapon.get("tier") or weapon.get("level")
            return f"{w_name} (T{w_tier})" if w_tier else str(w_name)
        if weapon:
            return str(weapon)

    sword_tier = p.get("sword_tier", 1)
    return f"Sword Tier {sword_tier}"


def _extract_dungeon_floor(p: dict) -> int:
    for key in ("dungeon_floor", "highest_dungeon_floor", "floor", "max_floor"):
        val = p.get(key)
        if isinstance(val, int):
            return val
        if isinstance(val, dict):
            for nested_key in ("floor", "highest", "current"):
                if isinstance(val.get(nested_key), int):
                    return val[nested_key]
    return 0


def _extract_pet_text(p: dict) -> tuple[str, int]:
    active_pet = p.get("active_pet") or p.get("equipped_pet")
    pets_data = p.get("pets")

    if isinstance(active_pet, dict):
        pet_name = active_pet.get("name") or active_pet.get("type") or "Pet"
        pet_lvl = int(active_pet.get("level", 1))
        return pet_name, pet_lvl

    if isinstance(active_pet, str) and active_pet.strip():
        pet_name = active_pet.strip()
        pet_lvl = 1
        if isinstance(pets_data, dict) and pet_name in pets_data and isinstance(pets_data[pet_name], dict):
            pet_lvl = int(pets_data[pet_name].get("level", 1))
        elif isinstance(pets_data, list):
            for entry in pets_data:
                if isinstance(entry, dict) and str(entry.get("name", "")).lower() == pet_name.lower():
                    pet_lvl = int(entry.get("level", 1))
                    break
        return pet_name.title(), pet_lvl

    if isinstance(pets_data, dict) and pets_data:
        first_key, first_val = next(iter(pets_data.items()))
        if isinstance(first_val, dict):
            return str(first_val.get("name") or first_key).title(), int(first_val.get("level", 1))
        return str(first_key).title(), 1

    return "None", 0


class StatsLeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View a player's RPG stats, weapon, dungeon floor, and active pet.")
    @app_commands.describe(member="Player to inspect (defaults to you)")
    async def stats(self, interaction: discord.Interaction, member: discord.Member | None = None):
        target = member or interaction.user
        uid = str(target.id)
        p = get_player(uid)

        if not isinstance(p, dict) or not p:
            return await interaction.response.send_message(
                f"❌ No RPG profile found for **{target.display_name}** yet.",
                ephemeral=True
            )

        wallet = int(p.get("wallet", 0))
        level = int(p.get("level", 1))
        xp = int(p.get("xp", 0))
        weapon_text = _extract_weapon_text(p)
        dungeon_floor = _extract_dungeon_floor(p)
        pet_name, pet_lvl = _extract_pet_text(p)

        pet_display = f"{pet_name} (Lv. {pet_lvl})" if pet_lvl > 0 else "None"

        embed = discord.Embed(
            title=f"📊 {target.display_name}'s RPG Stats",
            color=discord.Color.from_str("#4DF4FF")
        )
        embed.add_field(name="🪙 Balance", value=f"{wallet:,} coins", inline=True)
        embed.add_field(name="⭐ Level & XP", value=f"Lv. {level:,} ({xp:,} XP)", inline=True)
        embed.add_field(name="⚔️ Weapon", value=weapon_text, inline=True)
        embed.add_field(name="🏰 Dungeon Floor", value=f"Floor {dungeon_floor}", inline=True)
        embed.add_field(name="🐾 Active Pet", value=pet_display, inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View the top RPG players in this server.")
    @app_commands.describe(category="Ranking category")
    @app_commands.choices(category=[
        app_commands.Choice(name="Coins (Wallet)", value="wallet"),
        app_commands.Choice(name="Level & XP", value="level"),
        app_commands.Choice(name="Dungeon Floor", value="dungeon"),
    ])
    async def leaderboard(self, interaction: discord.Interaction, category: str = "wallet"):
        all_players = get_all_players()
        guild = interaction.guild

        rows = []
        for uid, p in all_players.items():
            if not isinstance(p, dict):
                continue

            uid_str = str(uid)
            member = guild.get_member(int(uid_str)) if (guild is not None and uid_str.isdigit()) else None
            if guild is not None and member is None:
                continue

            name = member.display_name if member else f"Adventurer ({uid_str})"
            wallet = int(p.get("wallet", 0))
            level = int(p.get("level", 1))
            xp = int(p.get("xp", 0))
            floor = _extract_dungeon_floor(p)
            pet_name, pet_lvl = _extract_pet_text(p)
            pet_tag = f" • 🐾 Lv.{pet_lvl}" if pet_lvl > 0 else ""

            if category == "level":
                score = (level, xp, wallet)
                stat_line = f"Lv. **{level:,}** *({xp:,} XP)*{pet_tag}"
            elif category == "dungeon":
                score = (floor, level, wallet)
                stat_line = f"Floor **{floor}** • Lv. {level:,}{pet_tag}"
            else:
                score = (wallet, level, xp)
                stat_line = f"🪙 **{wallet:,}** • Lv. {level:,}{pet_tag}"

            rows.append((score, name, stat_line))

        rows.sort(key=lambda r: r[0], reverse=True)
        top_10 = rows[:10]

        titles = {
            "wallet": "🪙 Server Coin Leaderboard",
            "level": "⭐ Server Level & XP Leaderboard",
            "dungeon": "🏰 Server Dungeon Floor Leaderboard",
        }
        medals = ["🥇", "🥈", "🥉"]

        embed = discord.Embed(
            title=titles.get(category, "🏆 Server Leaderboard"),
            color=discord.Color.from_str("#00BFFF")
        )

        if not top_10:
            embed.description = "No player stats found for this server yet!"
        else:
            lines = []
            for idx, (_, name, stat_line) in enumerate(top_10):
                prefix = medals[idx] if idx < 3 else f"**#{idx + 1}**"
                lines.append(f"{prefix} **{name}** — {stat_line}")
            embed.description = "\n".join(lines)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(StatsLeaderboardCog(bot))
