import discord
import chess

with open('token.txt') as tokenf:
    token = tokenf.read()

intents = discord.Intents(value=240640)
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

client.run(token)
