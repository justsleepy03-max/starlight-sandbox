import discord
from discord import app_commands
from discord.ext import commands


class HelpMenuView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "❌ This help menu doesn't belong to you! Run `/help` to open your own.",
                ephemeral=True,
            )
            return False
        return True

    def build_overview_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🌟 Starlight RPG — Quick Command Guide",
            description=(
                "Short on time? Tap a button below to jump straight to what you need:\n\n"
                "• **Overview** — This quick summary\n"
                "• **RPG Core** — `/profile`, `/hunt`, `/adventure`, `/gather`, `/heal`, `/daily`, `/quest`\n"
                "• **Gear & Coins** — `/gear`, `/craft`, `/shop`, `/inventory`, `/economy`, `/marketplace`, `/open`\n"
                "• **Spire, Guilds & Pets** — `/dungeon`, `/guild`, `/pets`, `/equip`\n"
                "• **Biomes & Tools** — `/area`, Area 2–15 unlocks, party games, `/stats`, `/leaderboard`, `/utility`, `/ticket`, `/feedback`"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Starlight Sandbox • Interactive Help Hub")
        return embed

    @discord.ui.button(label="Overview", style=discord.ButtonStyle.secondary, custom_id="hc_overview", row=0)
    async def overview_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=self.build_overview_embed(), view=self)

    @discord.ui.button(label="RPG Core", style=discord.ButtonStyle.primary, custom_id="hc_core", row=0)
    async def core_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="⚔️ Starlight RPG — Core Gameplay", color=discord.Color.blurple())
        embed.add_field(
            name="Start & Daily Loop",
            value=(
                "• `/profile` — Stats, biome, equipped gear & quick action buttons\n"
                "• `/hunt` — Fight monsters in your current biome\n"
                "• `/adventure` — Longer biome expeditions for bigger rewards\n"
                "• `/gather wood` / `fish` / `mine` — Collect materials *(Mine: Area 5+)*\n"
                "• `/heal` — Restore HP using bottles, elixirs, or life flasks"
            ),
            inline=False,
        )
        embed.add_field(
            name="Quests & Daily Coins",
            value=(
                "• `/daily` — Claim 500 coins every 24 hours\n"
                "• `/quest view` / `claim` / `abandon` — Track & turn in quests\n"
                "• `/givebundle` — Owner-only beta bundle command"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Gear & Coins", style=discord.ButtonStyle.success, custom_id="hc_gear_coins", row=0)
    async def gear_coins_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🛡️ Starlight RPG — Gear, Crafting & Economy", color=discord.Color.teal())
        embed.add_field(
            name="Gear & Crafting",
            value=(
                "• `/gear` — Equip swords & armor *(only unlocked/crafted tiers show up)*\n"
                "• `/craft` — Forge gear *(Crafted Sword: +15% Hunt Coins | Crafted Armor: +25% Gather)*\n"
                "• `/shop` & `/inventory` — Buy supplies, check items & view lootboxes\n"
                "• `/open` — Open lootboxes and mystery eggs"
            ),
            inline=False,
        )
        embed.add_field(
            name="Bank & Trading",
            value=(
                "• `/economy` — View wallet/bank balance, deposit, or withdraw\n"
                "• `/marketplace` — Trade and buy/sell items with players"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Spire, Guilds & Pets", style=discord.ButtonStyle.primary, custom_id="hc_endgame", row=1)
    async def endgame_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🏰 Starlight RPG — Spire, Guilds & Pets", color=discord.Color.purple())
        embed.add_field(
            name="Dungeons & Guilds",
            value=(
                "• `/dungeon` — Climb the 100-Floor Starlight Spire\n"
                "• `/guild` — Create, join, manage & level up guilds"
            ),
            inline=False,
        )
        embed.add_field(
            name="Companions & Loadouts",
            value=(
                "• `/pets` — Hatch, equip & level pets for passive buffs\n"
                "• `/equip` — Quick-equip tools and loadouts"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Biomes & Unlocks", style=discord.ButtonStyle.success, custom_id="hc_biomes", row=1)
    async def biomes_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🗺️ Starlight RPG — Biomes & Area Unlocks", color=discord.Color.green())
        embed.add_field(
            name="Area Travel",
            value="• `/area` — View all 15 biomes, level unlocks & travel via dropdown",
            inline=False,
        )
        embed.add_field(
            name="Areas 2–6",
            value="`/enchant`, `/training`, `/axe`, `/net`, `/pickup`, `/ladder`, `/farm`, `/multidice`, `/cook`, `/casino`, `/bowsaw`, `/boat`, `/pickaxe`",
            inline=False,
        )
        embed.add_field(
            name="Areas 7–12",
            value="`/refine`, `/big_arena`, `/alchemy`, `/tractor`, `/wheel`, `/chainsaw`, `/bigboat`, `/drill`, `/minintboss`, `/time_travel`, `/temporal_forge`, `/greenhouse`, `/dynamite`, `/petadventure`, `/ultraining`, `/badge`",
            inline=False,
        )
        embed.add_field(
            name="Areas 13–15",
            value="`/transmute`, `/hardmode hunt`, `/hardmode adventure`, `/big_dice`, `/time_jump`, `/transcend`",
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Games & Tools", style=discord.ButtonStyle.secondary, custom_id="hc_games_tools", row=1)
    async def games_tools_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎉 Starlight RPG — Party Games & Server Tools", color=discord.Color.gold())
        embed.add_field(
            name="Party Games",
            value=(
                "• `/cah` — Cards Against Humanity with buttons\n"
                "• `/trivia` — Interactive button trivia\n"
                "• `/connect4` — Connect Four with column buttons\n"
                "• `/bingo` — Generate a community Bingo card"
            ),
            inline=False,
        )
        embed.add_field(
            name="Stats, Utility & Support",
            value=(
                "• `/stats` & `/leaderboard` — Check stats and server rankings\n"
                "• `/utility` — Quick server & utility tools\n"
                "• `/ticket` & `/feedback` — Support tickets, bug reports & suggestions"
            ),
            inline=False,
        )
        await interaction.response.edit_message(embed=embed, view=self)


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Browse Starlight RPG commands using interactive buttons.")
    async def help(self, interaction: discord.Interaction):
        view = HelpMenuView(interaction.user.id)
        await interaction.response.send_message(embed=view.build_overview_embed(), view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
