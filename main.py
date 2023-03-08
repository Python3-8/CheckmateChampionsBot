from discord.ext import commands
from cairosvg import svg2png
from io import BytesIO
import datetime
import discord
import chess
import chess.svg
import chess.pgn

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
    if len(args) != 1:
        return await ctx.send('''\
/start-game usage:
`/start-game @DesiredOpponent`

The `start-game` command lets you play a game through Discord against any desired opponent.\
''')
    if author in mentions:
        return await ctx.send(f"Sorry {author.mention}, you cannot play yourself.")
    opponent = mentions[0]
    if find_game_index_with_user(author) is not None:
        return await ctx.send(f'Sorry {author.mention}, you are already in a game.')
    if find_game_index_with_user(opponent) is not None:
        return await ctx.send(f'Sorry {author.mention}, your desired opponent is already in a game.')
    game_index = len(games)
    games.append(((author, opponent), chess.Board()))
    await request_move(ctx, game_index)


@bot.command(name='mm')
async def make_move(ctx: commands.Context, *args: str):
    author = ctx.message.author
    if len(args) != 1:
        return await ctx.send('''\
/mm usage:
`/mm MoveInSAN`

The `mm` command lets you make a move (when it is your turn) in a chess game you are in.\
''')
    if (game_index := find_game_index_with_user(author)) is None:
        return await ctx.send(f'Sorry {author.mention}, you must be in a game in order to make a move.')
    move_san = args[0]
    players: tuple[discord.User | discord.Member]
    board: chess.Board
    players, board = games[game_index]
    user_to_play = players[not board.turn]
    if user_to_play != author:
        return await ctx.send(f"Sorry {author.mention}, it is currently your opponent {user_to_play.name}'s turn to play.")
    try:
        board.push_san(move_san)
    except chess.IllegalMoveError:
        return await ctx.send(f'Sorry {author.mention}, your move _{move_san}_ is an illegal move.')
    except chess.InvalidMoveError:
        return await ctx.send(f'Sorry {author.mention}, _{move_san}_ is invalid SAN.')
    except Exception:
        return await ctx.send(f'Sorry {author.mention}, an error occured while trying to make your move.')
    if board.is_checkmate():
        return await win(ctx, author, players[not players.index(
            author)], 'checkmate', game_index)
    elif board.is_stalemate():
        return await draw(ctx, 'stalemate', game_index)
    elif board.is_fivefold_repetition():
        return await draw(ctx, 'fivefold repetition', game_index)
    elif board.is_seventyfive_moves():
        return await draw(ctx, 'the seventy-five-move rule', game_index)
    await request_move(ctx, game_index)


@bot.command()
async def resign(ctx: commands.Context, *args: str):
    author = ctx.message.author
    if len(args) != 0:
        return await ctx.send('''\
/resign usage:
`/resign`

The `resign` command lets you withdraw from the chess game you are currently in, declaring your opponent as the victor.\
''')
    if (game_index := find_game_index_with_user(author)) is None:
        return await ctx.send(f'Sorry {author.mention}, you must be in a game in order to resign.')
    players = games[game_index][0]
    await win(ctx, players[not players.index(author)],
              author, 'resignation', game_index)


@bot.command(name='claim-draw')
async def claim_draw(ctx: commands.Context, *args: str):
    author = ctx.message.author
    if len(args) != 0:
        return await ctx.send('''\
/claim-draw usage:
`/claim-draw`

The `claim-draw` command lets you claim a draw during a game, if threefold repetition has occured or if the fifty-move rule applies.\
''')
    if (game_index := find_game_index_with_user(author)) is None:
        return await ctx.send(f'Sorry {author.mention}, you must be in a game in order to claim a draw.')
    players: discord.User | discord.Member
    board: chess.Board
    game = games[game_index]
    players, board = game
    opponent = players[not players.index(author)]
    if not board.can_claim_draw():
        return await ctx.send(f'Sorry {author.mention}, your game against {opponent.name} is not applicable for a draw claim.')
    if board.can_claim_threefold_repetition():
        return await draw(ctx, 'threefold repetition', game_index)
    await draw(ctx, 'the fifty-move rule', game_index)


async def request_move(ctx: commands.Context, game_index: int):
    players: tuple[discord.User | discord.Member]
    board: chess.Board
    players, board = games[game_index]
    white, black = players
    svg_raw = chess.svg.board(board, lastmove=board.move_stack[-1] if len(board.move_stack) else None, size=256, colors={
                              'square light': '#eeedd5', 'square dark': '#7c945d', 'square dark lastmove': '#bdc959', 'square light lastmove': '#f6f595'}, flipped=not board.turn)
    png_buffer = BytesIO()
    svg2png(bytestring=svg_raw, write_to=png_buffer, scale=2)
    png_buffer.seek(0)
    png_file = discord.File(png_buffer, 'board_state.png')
    await ctx.send(f"{white.mention if board.turn else white.name} vs. {black.name if board.turn else black.mention}\n{players[not board.turn].name}'s turn!", file=png_file)


async def win(ctx: commands.Context, winner: discord.User | discord.Member, loser: discord.User | discord.Member, reason: str, game_index: int):
    game = games[game_index]
    players: tuple[discord.User | discord.Member] = game[0]
    pgn = make_pgn(game, result='1-0' if players[0] == winner else '0-1')
    games.pop(game_index)
    await ctx.send(f'{winner.mention} wins against {loser.mention} by {reason}!\n\n```\n{pgn}\n```')


async def draw(ctx: commands.Context, reason: str, game_index: int):
    game = games[game_index]
    players: tuple[discord.User | discord.Member] = game[0]
    pgn = make_pgn(game, result='1/2-1/2')
    games.pop(game_index)
    await ctx.send(f'Game between {players[0].mention} and {players[1].mention} drawn by {reason}!\n\n```\n{pgn}\n```')


def find_game_index_with_user(user: discord.User | discord.Member):
    for players, board in games:
        if user in players:
            return games.index((players, board))
    return None


def make_pgn(game: tuple[tuple[discord.User | discord.Member] | chess.Board], result: str):
    white: tuple[discord.User | discord.Member]
    black: tuple[discord.User | discord.Member]
    board: chess.Board
    (white, black), board = game
    pgn = chess.pgn.Game()
    pgn.headers['Event'] = f'{white.name} vs. {black.name}'
    pgn.headers['Site'] = 'Checkmate Champions @ Discord'
    pgn.headers['Date'] = datetime.date.today().strftime('%Y.%m.%d')
    pgn.headers['White'] = white
    pgn.headers['Black'] = black
    pgn.headers['Result'] = result
    last_node = pgn
    for move in board.move_stack:
        new_node = last_node.add_variation(move)
        last_node = new_node
    return str(pgn)


games: list[tuple[tuple[discord.User | discord.Member] | chess.Board]] = []

bot.run(token)
