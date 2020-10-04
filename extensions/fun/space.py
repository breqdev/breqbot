import random

from . import game


class Space(game.Game):
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
