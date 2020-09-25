import random
import asyncio

import discord
from discord.ext import commands

from .utils import *

class Games(BaseCog):
    "A cog with some simple games"

    @commands.command()
    @passfail
    async def space(self, ctx):
        "Game where you can walk around"

        embed = discord.Embed()

        field = [
            ["🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "⬛", "⬛", "⬛", "⬛", "⬛", "⬛", "🟧"],
            ["🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧", "🟧"]
        ]

        async def draw_field(message=None):
            text = "\n".join("".join(pixel for pixel in row) for row in field)
            if message:
                return await message.edit(content=text)
            else:
                return await ctx.send(text)

        player_colors = ["🟦", "🟩", "🟪", "🟥"]
        players = {}

        moves = {"⬆️": (0, -1),
                 "➡️": (1, 0),
                 "⬇️": (0, 1),
                 "⬅️": (-1, 0)
        }

        class Player:
            def __init__(self):
                # Pick an open position in the field
                self.x, self.y = 0, 0
                while field[self.y][self.x] != "⬛":
                    self.x = random.randint(1, 7)
                    self.y = random.randint(1, 7)

                # Choose an unused color
                self.color = player_colors[len(players)]

                field[self.y][self.x] = self.color

            def move_to(self, x, y):
                field[self.y][self.x] = "⬛"
                self.x, self.y = x, y
                field[self.y][self.x] = self.color

            def move(self, dx, dy):
                if abs(dx) + abs(dy) != 1:
                    return False

                final_pos = field[self.y+dy][self.x+dx]
                if final_pos != "⬛":
                    return False

                self.move_to(self.x+dx, self.y+dy)
                return True

        players[ctx.author.id] = Player()

        message = await draw_field()

        for emoji in moves:
            await message.add_reaction(emoji)
        await message.add_reaction("🆕")

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id != self.bot.user.id)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=120, check=check)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                return NoReact
            else:
                if user.id in players:
                    if reaction.emoji in moves:
                        players[user.id].move(*moves[reaction.emoji])
                else:
                    if reaction.emoji == "🆕":
                        players[user.id] = Player()
                await reaction.remove(user)
                await draw_field(message)

    @commands.command(name="2048")
    @passfail
    async def game2048(self, ctx):
        "Play a version of the classic 2048 game"

        numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        moves = ["⬆️", "➡️", "⬇️", "⬅️"]

        #grid = [["⬛" for _ in range(4)] for _ in range(4)]
        grid = [["0️⃣" for _ in range(4)] for _ in range(4)]

        def add_random():
            x, y = random.randint(0, 3), random.randint(0, 3)
            while grid[y][x] != "⬛":
                x, y = random.randint(0, 3), random.randint(0, 3)

            tile = "2️⃣" if (random.random() > 0.9) else "1️⃣"

            grid[y][x] = tile

        # add_random()

        def check_full():
            for row in grid:
                for square in row:
                    if square == "⬛":
                        return False
            return True

        def process_move(move):
            # TODO: process move

            if check_full():
                return False

            add_random()
            return True

        messages = []
        for row in grid:
            messages.append(await ctx.send("".join(row)))
        message = messages[-1]  # message used for reactions

        for move in moves:
            await message.add_reaction(move)

        frame = [0]

        async def draw():
            frame[0] += 1
            grid_copy = [row[:] for row in grid]
            if frame[0] % 2:
                for row in grid_copy:
                    for i, char in enumerate(row):
                        if char == "⬛":
                            row[i] = "⬜"

            for message, row in zip(messages, grid_copy):
                await asyncio.sleep(0.2)
                await message.edit(content="".join(row))

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id != self.bot.user.id)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=120, check=check)
            except asyncio.TimeoutError:
                await message.clear_reactions()
                return NoReact
            else:
                if reaction.emoji in moves:
                    if not process_move(reaction.emoji):
                        await draw()
                        await message.clear_reactions()

                        for character in text_to_emoji("game ovr").split(" "):
                            await message.add_reaction(character)
                        return NoReact
                await reaction.remove(user)
                await draw()

def setup(bot):
    bot.add_cog(Games(bot))
