import discord
from discord.ext import commands
import chess
import pprint

with open('token.txt') as tokenf:
    token = tokenf.read()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)


@bot.command(name='start-game')
async def start_game(ctx: commands.Context, *args: str):
    author = ctx.message.author
    mentions = ctx.message.mentions
    if author in mentions:
        return await ctx.send(f"Sorry {author.mention}, you can't play yourself.")
    if len(mentions) > 1:
        return await ctx.send(f'Sorry {author.mention}, I currently only support two player chess.')

games: dict[tuple[discord.User | discord.Member], chess.Board] = {}

bot.run(token)
