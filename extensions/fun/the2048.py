import random

from .. import emoji_utils
from . import game


class The2048(game.Game):
    desc = ("Play a version of the classic 2048 game "
            ":two: :zero: :four: :eight:")

    async def init(self):
        self.message = None
        self.running = True

        # self.numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣",
        #                 "4️⃣", "5️⃣", "6️⃣", "7️⃣",
        #                 "8️⃣", "9️⃣", "🔟", "⭐"]
        number_names = ["4096", "2_", "4_", "8_", "16", "32", "64",
                        "128", "256", "512", "1024", "2048"]
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

        for character in emoji_utils.text_to_emoji("game ovr").split(" "):
            await self.message.add_reaction(character)

    async def show_win(self):
        await self.draw()
        await self.message.clear_reactions()

        for character in emoji_utils.text_to_emoji("you win").split(" "):
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
