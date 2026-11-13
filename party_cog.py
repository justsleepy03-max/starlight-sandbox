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
    "A majestic beard.", "Uncontrollable sobbing.", "A balanced breakfast.",
    "Dabbing.", "Vigorous high-fives.", "A disappointed look from your mother.",
    "Accidentally texting your boss a meme.", "Overwhelming dread.",
    "A poorly timed sneeze.", "Tactical nuke incoming.", "Four decades of bad decisions.", "A single lonely Dorito."
]

# --- TRIVIA DATA ---
TRIVIA_QUESTIONS = [
    {"q": "What year was the original PlayStation released?", "choices": ["1990", "1994", "1998", "2001"], "answer": "1994"},
    {"q": "Which planet in our solar system is the hottest?", "choices": ["Mercury", "Venus", "Mars", "Jupiter"], "answer": "Venus"},
    {"q": "What is the highest-grossing video game franchise of all time?", "choices": ["Pokémon", "Call of Duty", "Mario", "Minecraft"], "answer": "Pokémon"},
    {"q": "Which anime features a notebook that kills anyone whose name is written in it?", "choices": ["Naruto", "Bleach", "Death Note", "Attack on Titan"], "answer": "Death Note"},
]

# --- TRUTH OR DARE DATA ---
TRUTHS = [
    "What is the most embarrassing thing you've ever done while gaming?",
    "If you could live inside any video game world for a year, which one would it be?",
    "What's a secret guilty pleasure food combination you love?",
    "What was your very first video game console?"
]

DARES = [
    "Send the last saved meme from your phone camera roll to chat.",
    "Speak only in pirate lingo for the next 10 minutes.",
    "Type your next three messages using only emojis.",
    "Change your Discord nickname to 'PotatoLord' for the next hour."
]

UNO_COLORS = ["🔴 Red", "🔵 Blue", "🟢 Green", "🟡 Yellow"]
UNO_VALUES = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Skip", "Reverse", "+2"]

# --- INTERACTIVE VIEWS ---

class TriviaView(discord.ui.View):
    def __init__(self, choices, correct_answer):
        super().__init__(timeout=30)
        self.correct_answer = correct_answer
        for i, choice in enumerate(choices):
            btn = discord.ui.Button(label=f"{i+1}. {choice}", style=discord.ButtonStyle.primary, custom_id=f"trivia_{i}")
            btn.callback = self.make_callback(choice)
            self.add_item(btn)

    def make_callback(self, choice):
        async def callback(interaction: discord.Interaction):
            if choice == self.correct_answer:
                await interaction.response.send_message(f"🎉 **Correct!** {interaction.user.mention} got the right answer: **{choice}**!", ephemeral=False)
            else:
                await interaction.response.send_message(f"❌ **Incorrect!** Sorry {interaction.user.mention}, the correct answer was **{self.correct_answer}**.", ephemeral=True)
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)
        return callback

class CAHView(discord.ui.View):
    def __init__(self, hand):
        super().__init__(timeout=45)
        for i, card in enumerate(hand):
            btn = discord.ui.Button(label=f"Card {i+1}", style=discord.ButtonStyle.secondary, custom_id=f"cah_{i}")
            btn.callback = self.make_callback(card)
            self.add_item(btn)

    def make_callback(self, card):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(f"🃏 {interaction.user.mention} played: **{card}**", ephemeral=False)
        return callback

class ConnectFourView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        for col in range(1, 8):
            btn = discord.ui.Button(label=str(col), style=discord.ButtonStyle.success, custom_id=f"c4_{col}")
            btn.callback = self.make_callback(col)
            self.add_item(btn)

    def make_callback(self, col):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(f"🔴 **{interaction.user.display_name}** dropped a piece into column **{col}**!", ephemeral=False)
        return callback


class PartyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="cah", description="Play an interactive round of Cards Against Humanity!")
    async def cah(self, interaction: discord.Interaction):
        black_card = random.choice(BLACK_CARDS)
        hand = random.sample(WHITE_CARDS, 3)
        
        embed = discord.Embed(title="🃏 Cards Against Humanity - Starlight Edition", color=discord.Color.dark_theme())
        embed.add_field(name="BLACK PROMPT", value=f"**{black_card}**", inline=False)
        
        hand_text = "\n".join([f"{i+1}️⃣ {card}" for i, card in enumerate(hand)])
        embed.add_field(name=f"{interaction.user.display_name}'s Hand", value=hand_text, inline=False)
        embed.set_footer(text="Click a button below to play your card!")
        
        view = CAHView(hand)
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="trivia", description="Test your knowledge with interactive trivia buttons!")
    async def trivia(self, interaction: discord.Interaction):
        q_data = random.choice(TRIVIA_QUESTIONS)
        embed = discord.Embed(title="❓ Starlight Trivia Challenge", description=f"**{q_data['q']}**", color=discord.Color.blue())
        
        choices_text = "\n".join([f"{i+1}️⃣ {choice}" for i, choice in enumerate(q_data['choices'])])
        embed.add_field(name="Options", value=choices_text, inline=False)
        embed.set_footer(text="Click the matching button below to answer!")
        
        view = TriviaView(q_data['choices'], q_data['answer'])
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="truth", description="Get a random truth question!")
    async def truth(self, interaction: discord.Interaction):
        t = random.choice(TRUTHS)
        embed = discord.Embed(title=f"🤔 Truth for {interaction.user.display_name}", description=f"*{t}*", color=discord.Color.purple())
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="dare", description="Get a random server dare!")
    async def dare(self, interaction: discord.Interaction):
        d = random.choice(DARES)
        embed = discord.Embed(title=f"🔥 Dare for {interaction.user.display_name}", description=f"*{d}*", color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="connect4", description="Start an interactive game of Connect Four!")
    async def connect4(self, interaction: discord.Interaction):
        board = [["⚪" for _ in range(7)] for _ in range(6)]
        board_str = "\n".join([" ".join(row) for row in board])
        board_str += "\n1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣"
        
        embed = discord.Embed(title="🔴 Connect Four 🟡", description=board_str, color=discord.Color.gold())
        embed.set_footer(text="Click a column button below to place your piece!")
        
        view = ConnectFourView()
        await interaction.response.send_message(embed=embed, view=view)

    @discord.app_commands.command(name="wordchain", description="Start or continue the Word Chain game!")
    @discord.app_commands.describe(word="Your word starting with the last letter of the previous word")
    async def wordchain(self, interaction: discord.Interaction, word: str):
        word = word.lower()
        last_letter = word[-1]
        embed = discord.Embed(title="🔗 Word Chain", description=f"**{interaction.user.display_name}** played: **{word.upper()}**\n\nNext player must say a word starting with **{last_letter.upper()}**!", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="mafia", description="Assign random secret roles for a game of Mafia!")
    async def mafia(self, interaction: discord.Interaction):
        roles = ["🕵️ Detective", "🩺 Doctor", "🔫 Mafia", "👥 Townsperson", "👥 Townsperson"]
        assigned = random.choice(roles)
        
        try:
            await interaction.user.send(f"🕵️ Your secret Mafia role in **{interaction.guild.name}** is: **{assigned}**")
            await interaction.response.send_message(f"🕵️ **{interaction.user.display_name}** has been assigned their secret role via Direct Message!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I couldn't DM you your role! Please enable DMs from server members.", ephemeral=True)

    @discord.app_commands.command(name="bingo", description="Generate a community Bingo card!")
    async def bingo(self, interaction: discord.Interaction):
        numbers = random.sample(range(1, 76), 25)
        numbers[12] = "⭐ FREE"
        
        grid_rows = []
        for i in range(0, 25, 5):
            row = " | ".join([f"{num:2}" if isinstance(num, int) else f"{num}" for num in numbers[i:i+5]])
            grid_rows.append(row)
            
        board_text = "```\n" + "\n-----\n".join(grid_rows) + "\n```"
        embed = discord.Embed(title=f"🎯 {interaction.user.display_name}'s Bingo Card", description=board_text, color=discord.Color.gold())
        embed.set_footer(text="Mark your numbers as they're called! First to complete a line wins!")
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="uno", description="Draw a random starting Uno card for a game!")
    async def uno(self, interaction: discord.Interaction):
        card_color = random.choice(UNO_COLORS)
        card_val = random.choice(UNO_VALUES)
        
        embed = discord.Embed(title="🃏 Uno Hand Draw", description=f"Your card is: **{card_color} {card_val}**", color=discord.Color.orange())
        embed.set_footer(text="Play matching colors or numbers!")
        await interaction.response.send_message(embed=embed
