import discord
from discord.ext import commands
import random

# --- CARDS AGAINST HUMANITY DATA ---
BLACK_CARDS = [
    "Why can't I sleep at night? _",
    "I got 99 problems, but _ ain't one.",
    "What's that smell? _",
    "In 1,000 years, how will we pay for goods and services? _",
    "What secret desire does Batman harbor? _",
    "What is my secret superpower? _",
    "What did I bring back from the time machine? _",
    "What's the best part of waking up? _",
    "Step 1: _. Step 2: Profit."
]

WHITE_CARDS = [
    "Accidentally eating a live spider.",
    "A deeply unsettling amount of cheese.",
    "Throwing a toaster into a hot tub.",
    "Uncontrollable screaming.",
    "A slow Wi-Fi connection.",
    "Getting caught sleepwalking in a Denny's parking lot.",
    "Absolute silence.",
    "A pigeon with an attitude problem."
]

# --- TRIVIA DATA ---
TRIVIA_QUESTIONS = [
    {"question": "What is the capital of France?", "options": ["London", "Berlin", "Paris", "Madrid"], "answer": "Paris"},
    {"question": "Which planet is known as the Red Planet?", "options": ["Venus", "Mars", "Jupiter", "Saturn"], "answer": "Mars"},
    {"question": "What is 5 + 5 * 2?", "options": ["20", "15", "10", "25"], "answer": "15"},
    {"question": "Which programming language shares its name with a snake?", "options": ["Java", "Python", "C++", "Ruby"], "answer": "Python"}
]

# --- UNO DATA ---
UNO_COLORS = ["Red", "Blue", "Green", "Yellow"]
UNO_VALUES = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "Skip", "Reverse", "Draw Two"]

class PartyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="cah", description="Play a quick round of Cards Against Humanity!")
    async def cah(self, interaction: discord.Interaction):
        black_card = random.choice(BLACK_CARDS)
        white_card = random.choice(WHITE_CARDS)
        filled_card = black_card.replace("_", f"**{white_card}**")

        embed = discord.Embed(title="🃏 Cards Against Humanity", description=filled_card, color=discord.Color.dark_embed())
        embed.set_footer(text=f"Played by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="trivia", description="Test your knowledge with a trivia question!")
    async def trivia(self, interaction: discord.Interaction):
        q = random.choice(TRIVIA_QUESTIONS)
        embed = discord.Embed(title="🧠 Trivia Time!", description=q["question"], color=discord.Color.blue())
        for idx, option in enumerate(q["options"], 1):
            embed.add_field(name=f"Option {idx}", value=option, inline=False)
        embed.set_footer(text=f"Answer: {q['answer']} (Just for fun!)")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="connect4", description="Drop a Connect Four game preview board!")
    async def connect4(self, interaction: discord.Interaction):
        board = "⚪ " * 7 + "\n" + ("🟡 🔴 ⚪ 🟡 🔴 ⚪ 🟡\n" * 5)
        embed = discord.Embed(title="🔴 Connect Four 🟡", description=board, color=discord.Color.gold())
        embed.set_footer(text=f"Challenged by {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="bingo", description="Generate a random Bingo card number grid!")
    async def bingo(self, interaction: discord.Interaction):
        numbers = list(range(1, 76))
        random.shuffle(numbers)
        board_numbers = numbers[:25]
        board_numbers[12] = "FREE"

        grid_rows = []
        for i in range(0, 25, 5):
            row = " | ".join([f"{str(num):2}" for num in board_numbers[i:i+5]])
            grid_rows.append(row)

        board_text = "```\n" + "\n-----\n".join(grid_rows) + "\n```"
        embed = discord.Embed(title=f"🎟️ {interaction.user.display_name}'s Bingo Card", description=board_text, color=discord.Color.green())
        embed.set_footer(text="Mark your numbers as they're called! First to complete a line wins!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="uno", description="Draw a random starting Uno card for a game!")
    async def uno(self, interaction: discord.Interaction):
        card_color = random.choice(UNO_COLORS)
        card_val = random.choice(UNO_VALUES)

        embed = discord.Embed(title="🎟️ Uno Hand Draw", description=f"Your card is: **{card_color} {card_val}**", color=discord.Color.blue())
        embed.set_footer(text="Play matching colors or numbers!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="wordchain", description="Start a Word Chain game prompt!")
    async def wordchain(self, interaction: discord.Interaction):
        starting_word = random.choice(["Dragon", "Galaxy", "Coffee", "Python", "Shadow", "Rocket"])
        embed = discord.Embed(title="⛓️ Word Chain", description=f"The starting word is: **{starting_word}**\nReply with a word starting with the last letter!", color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="truth", description="Get a random Truth prompt!")
    async def truth(self, interaction: discord.Interaction):
        prompts = [
            "What is the weirdest food combination you secretly enjoy?",
            "If you could live in any video game world, which one would it be?",
            "What was your most embarrassing moment in an online game?"
        ]
        embed = discord.Embed(title="🤫 Truth", description=random.choice(prompts), color=discord.Color.teal())
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="dare", description="Get a random Dare prompt!")
    async def dare(self, interaction: discord.Interaction):
        prompts = [
            "Type your next three messages using only emojis.",
            "Send a screenshot of your current desktop wallpaper in chat.",
            "Compliment the person above you in the most dramatic way possible."
        ]
        embed = discord.Embed(title="🔥 Dare", description=random.choice(prompts), color=discord.Color.orange())
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="mafia", description="Assign a secret party game role!")
    async def mafia(self, interaction: discord.Interaction):
        roles = ["Mafia", "Detective", "Doctor", "Civilian", "Civilian", "Civilian"]
        assigned_role = random.choice(roles)
        await interaction.user.send(f"🤫 Your secret role for this game is: **{assigned_role}**")
        await interaction.response.send_message("🕵️ Roles have been secretly assigned via DM!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PartyCog(bot))
