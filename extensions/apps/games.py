import random
import asyncio
import typing
import os

import discord
from discord.ext import commands

from .utils import *


class Game():
    def __init__(self, ctx, args):
        self.ctx = ctx
        self.args = args.split(" ") if args else []

    async def get_emoji(self, emoji_name):
        guild = self.ctx.bot.get_guild(int(os.getenv("CONFIG_GUILD")))
        for emoji in guild.emojis:
            if emoji.name == emoji_name:
                return str(emoji)


class SpaceGame(Game):
    desc = "Game where you can walk around :space_invader:"

    async def init(self):
        self.message = None
        self.running = True

        self.field = [
            ["🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧"]
        ]

        self.player_colors = ["🟦", "🟩", "🟪", "🟥"]
        self.players = {}

        self.moves = {
            "⬆️": (0, -1),
            "➡️": (1, 0),
            "⬇️": (0, 1),
            "⬅️": (-1, 0)
        }

    async def new_player(game, user):
        class Player:
            def __init__(self):
                # Pick an open position in the field
                self.x, self.y = 0, 0
                while game.field[self.y][self.x] != "⬛":
                    self.x = random.randint(1, 7)
                    self.y = random.randint(1, 7)

                # Choose an unused color
                self.color = game.player_colors[len(game.players)]

                game.field[self.y][self.x] = self.color

            def move_to(self, x, y):
                game.field[self.y][self.x] = "⬛"
                self.x, self.y = x, y
                game.field[self.y][self.x] = self.color

            def move(self, dx, dy):
                if abs(dx) + abs(dy) != 1:
                    return False

                final_pos = game.field[self.y+dy][self.x+dx]
                if final_pos != "⬛":
                    return False

                self.move_to(self.x+dx, self.y+dy)
                return True

        game.players[user.id] = Player()

    async def draw(self):
        text = "\n".join("".join(pixel for pixel in row) for row in self.field)
        if self.message:
            return await self.message.edit(content=text)
        else:
            self.message = await self.ctx.send(text)

            for emoji in self.moves:
                await self.message.add_reaction(emoji)
            await self.message.add_reaction("🆕")
            await self.message.add_reaction("❌")

            return self.message

    async def move(self, user, emoji):
        if emoji == "❌":
            await self.timeout()
            self.running = False
        if user.id in self.players:
            if emoji in self.moves:
                self.players[user.id].move(*self.moves[emoji])
        else:
            if emoji == "🆕":
                self.new_player(user)

    async def timeout(self):
        await self.message.clear_reactions()

    async def game_over(self):
        await self.message.clear_reactions()


class The2048Game(Game):
    desc = "Play a version of the classic 2048 game :two: :zero: :four: :eight:"
    async def init(self):
        self.message = None
        self.running = True

        # self.numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟", "⭐"]
        number_names = ["4096", "2_", "4_", "8_", "16", "32", "64", "128", "256", "512", "1024", "2048"]
        self.numbers = [await self.get_emoji(name) for name in number_names]

        self.moves = ["⬆️", "➡️", "⬇️", "⬅️"]

        self.grid = [["⬛" for _ in range(4)] for _ in range(4)]

        self.add_random()
        self.add_random()

    async def new_player(self, user):
        self.player = user

    def add_random(self):
        x, y = random.randint(0, 3), random.randint(0, 3)
        while self.grid[y][x] != "⬛":
            x, y = random.randint(0, 3), random.randint(0, 3)

        tile = self.numbers[2] if (random.random() > 0.9) else self.numbers[1]
        self.grid[y][x] = tile

    @property
    def full(self):
        for row in self.grid:
            for square in row:
                if square == "⬛":
                    return False
        return True

    @property
    def winnable(self):
        if not self.full:
            return True
        # Check rows
        for y in range(4):
            for x in range(3):
                if self.grid[y][x] == self.grid[y][x+1]:
                    return True
        # Check cols
        for x in range(4):
            for y in range(3):
                if self.grid[y][x] == self.grid[y+1][x]:
                    return True
        return False

    @property
    def won(self):
        for row in self.grid:
            for square in row:
                if square == self.numbers[11]:
                    return True
        return False

    async def game_over(self):
        await self.draw()
        await self.message.clear_reactions()

        for character in text_to_emoji("game ovr").split(" "):
            await self.message.add_reaction(character)

    async def show_win(self):
        await self.draw()
        await self.message.clear_reactions()

        for character in text_to_emoji("you win").split(" "):
            await self.message.add_reaction(character)

    def compress_row_to_left(self, row):
        changes_made = False
        for idx_to_fill in range(3):
            if row[idx_to_fill] != "⬛":
                continue  # occupied
            for idx_to_pull in range(idx_to_fill+1, 4):
                if row[idx_to_pull] != "⬛":
                    tile_to_move = row[idx_to_pull]
                    row[idx_to_pull] = "⬛"
                    row[idx_to_fill] = tile_to_move
                    changes_made = True
                    break
        return changes_made

    def merge_row_to_left(self, row):
        changes_made = False

        index = 0
        while index < 3:
            if row[index] != "⬛" and row[index] == row[index+1]:
                number = self.numbers.index(row[index]) + 1
                row[index] = self.numbers[number]

                for shift_index in range(index+1, 3):
                    row[shift_index] = row[shift_index+1]

                row[3] = "⬛"

                changes_made = True
            else:
                index += 1

        if changes_made:
            self.merge_row_to_left(row)
            return True
        else:
            return False

    def move_left(self):
        changes_made = False
        for row in self.grid:
            changes_made = self.compress_row_to_left(row) or changes_made
            changes_made = self.merge_row_to_left(row) or changes_made
            changes_made = self.compress_row_to_left(row) or changes_made
        return changes_made

    def move_right(self):
        for row in self.grid:
            row.reverse()

        changes_made = self.move_left()

        for row in self.grid:
            row.reverse()

        return changes_made

    def transpose(self):
        self.grid = list(map(list, zip(*self.grid)))

    def move_up(self):
        self.transpose()
        changes_made = self.move_left()
        self.transpose()
        return changes_made

    def move_down(self):
        self.transpose()
        changes_made = self.move_right()
        self.transpose()
        return changes_made

    def move_grid(self, emoji):
        if emoji == "⬅️":
            return self.move_left()
        elif emoji == "➡️":
            return self.move_right()
        elif emoji == "⬆️":
            return self.move_up()
        elif emoji == "⬇️":
            return self.move_down()
        return False

    async def move(self, user, emoji):
        if "single" in self.args:
            if user.id != self.player.id:
                return

        if emoji == "❌":
            await self.timeout()
            self.running = False

        board_changed = self.move_grid(emoji)

        if board_changed and not self.full:
            self.add_random()

        await self.draw()

        if not self.winnable:
            await self.game_over()
            self.running = False

        if self.won:
            await self.show_win()
            self.running = False

    async def draw(self):
        text = "\n".join("".join(row) for row in self.grid)
        if self.message:
            await self.message.edit(content=text)
        else:
            self.message = await self.ctx.send(text)
            for emoji in self.moves:
                await self.message.add_reaction(emoji)
            await self.message.add_reaction("❌")
            return self.message

    async def timeout(self):
        await self.message.clear_reactions()

class BaseGames(BaseCog):
    async def play(self, ctx, GameType, args):
        game = GameType(ctx, args)
        await game.init()
        await game.new_player(ctx.author)

        message = await game.draw()

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id != self.bot.user.id)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=3600, check=check)
            except asyncio.TimeoutError:
                await game.timeout()
                return NoReact
            else:
                await game.move(user, reaction.emoji)
                await reaction.remove(user)
                await game.draw()
                if not game.running:
                    return NoReact

games = {
    "space": SpaceGame,
    "2048": The2048Game,
}

def make_command(name, game):
    @commands.command(name=name, brief=game.desc)
    @commands.guild_only()
    @passfail
    async def _command(self, ctx, *, args: typing.Optional[str] = None):
        return await self.play(ctx, game, args)

    return _command


new_commands = {}
for name, game in games.items():
    new_commands[name] = make_command(name, game)

Games = type("Games", (BaseGames,), new_commands)
Games.description = "Play a few simple games right in Discord"

def setup(bot):
    bot.add_cog(Games(bot))
