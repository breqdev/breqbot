import typing

from discord.ext import commands, tasks

from ..base import BaseCog

from . import animegirl
from . import xkcd
from . import testcomic


class BaseComics(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.watch_task.start()

    async def add_watch(self, series, channel_id):
        self.redis.sadd(f"comic:watching:{series}", channel_id)

    async def rem_watch(self, series, channel_id):
        self.redis.srem(f"comic:watching:{series}", channel_id)

    async def is_watching(self, series, channel_id):
        return self.redis.sismember(f"comic:watching:{series}", channel_id)

    @tasks.loop(minutes=15)
    async def watch_task(self):
        for name, comic in self.comics.items():
            new_hash = await comic.get_hash()
            old_hash = self.redis.get(f"comic:hash:{name}")
            if old_hash != new_hash:
                self.redis.set(f"comic:hash:{name}", new_hash)
                for channel_id in \
                        self.redis.smembers(f"comic:watching:{name}"):
                    channel = self.bot.get_channel(int(channel_id))
                    await self.pack_send(
                        channel, *(await comic.get_post("latest")))


comics = {
    "animegirl": animegirl.AnimeGirl(),
    "xkcd": xkcd.XKCD(),
    "testcomic": testcomic.TestComic()
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
