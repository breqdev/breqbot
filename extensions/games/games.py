import asyncio
import typing

from discord.ext import commands

from .. import base

from . import space, the2048, soundboard


class BaseGames(base.BaseCog):
    async def play(self, ctx, GameType, args):
        game = GameType(ctx, args, self.redis)
        await game.init()
        if not game.running:
            return
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
                return
            else:
                await game.move(user, reaction.emoji)
                await reaction.remove(user)
                await game.draw()
                if not game.running:
                    return


games = {
    "space": space.Space,
    "2048": the2048.The2048,
    "soundboard": soundboard.Soundboard,
}


def make_command(name, game):
    @commands.command(name=name, brief=game.desc)
    @commands.guild_only()
    async def _command(self, ctx, *, args: typing.Optional[str] = None):
        await self.play(ctx, game, args)

    return _command


new_commands = {}
for name, game in games.items():
    new_commands[name] = make_command(name, game)

Games = type("Games", (BaseGames,), new_commands)
Games.description = "Play a few simple games right in Discord"


def setup(bot):
    bot.add_cog(Games(bot))
