import typing

from discord.ext import commands

from .. import publisher

from . import animegirl
from . import xkcd


class BaseComics(publisher.PublisherCog):
    watch_params = ("comic name",)

    def __init__(self, bot):
        super().__init__(bot)

    async def get_hash(self, series):
        return await self.comics[series].get_hash()

    async def get_update(self, series):
        return await self.comics[series].get_post("latest")


comics = {
    "animegirl": animegirl.AnimeGirl(),
    "xkcd": xkcd.XKCD(),
}


def make_command(name, comic):
    @commands.command(name=name, brief=comic.__doc__)
    async def _command(self, ctx, *, number: typing.Optional[str] = "random"):
        await self.pack_send(ctx, *(await comic.get_post(number)))

    return _command


new_commands = {}
for name, comic in comics.items():
    new_commands[name] = make_command(name, comic)

Comics = type("Comics", (BaseComics,), new_commands)
Comics.comics = comics
Comics.description = "View a variety of cool comics!"


def setup(bot):
    bot.add_cog(Comics(bot))
