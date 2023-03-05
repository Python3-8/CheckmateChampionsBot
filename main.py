import discord
import chess

with open('token.txt') as tokenf:
    token = tokenf.read()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    if message.content.startswith('/'):
        await exec_command(message)


async def exec_command(message: discord.Message):
    words = message.content.split()
    command = commands.get(words[0][1:])
    if command:
        await command(message, args=words[1:])


async def start_game(message: discord.Message, *, args: list[str]):
    print(f'command: start_game, {args=}')
    await message.channel.send(f'command: start_game, {args=}')


games: dict[tuple[discord.User | discord.Member], chess.Board] = {}
commands = {'start-game': start_game}

client.run(token)
