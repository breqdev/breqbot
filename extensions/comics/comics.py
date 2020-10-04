import typing

from discord.ext import commands, tasks

from ..base import BaseCog

from . import animegirl
from . import xkcd


class BaseComics(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.watching = {comic: [] for comic in self.comics}

    async def init_hashes(self):
        self.hashes = {comic: await comic.get_hash() for comic in self.comics}
        self.watch_task.start()

    async def add_watch(self, series, channel_id):
        self.watching[series].append(channel_id)

    async def rem_watch(self, series, channel_id):
        self.watching[series].remove(channel_id)

    async def is_watching(self, series, channel_id):
        return channel_id in self.watching[series]

    @tasks.loop(minutes=15)
    async def watch_task(self):
        for comic in self.watching:
            new_hash = await comic.get_hash()
            if self.hashes[comic] != new_hash:
                self.hashes[comic] = new_hash
                for channel_id in self.watching[comic]:
                    channel = self.bot.get_channel(channel_id)
                    await self.pack_send(channel,
                                         *(await comic.get_post("latest")))


comics = {
    "animegirl": animegirl.AnimeGirl(),
    "xkcd": xkcd.XKCD(),
}


def make_command(name, comic):
    @commands.command(name=name, brief=comic.__doc__)
    async def _command(self, ctx, *, number: typing.Optional[str] = "random"):
        if number == "watch":
            await self.add_watch(name, ctx.channel.id)
            await ctx.message.add_reaction("✅")
        elif number == "unwatch":
            await self.rem_watch(name, ctx.channel.id)
            await ctx.message.add_reaction("✅")
        elif number == "watching":
            if await self.is_watching(name, ctx.channel.id):
                await ctx.send(
                    f"{ctx.channel.mention} is currently watching {name}.")
            else:
                await ctx.send(
                    f"{ctx.channel.mention} is not currently watching {name}.")
        else:
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
