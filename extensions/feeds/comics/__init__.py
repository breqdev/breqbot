import typing

import aiohttp
import aiocron
import discord
from discord.ext import commands

from ... import base

from . import animegirl, xkcd, testcomic


class BaseComics(base.BaseCog):

    description = "View a variety of cool comics!"
    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()
        # Note: discord.py does not run coroutines on Cog unload
        # see (https://discordpy.readthedocs.io/en/latest/ext/
        #      commands/api.html#discord.ext.commands.Cog.cog_unload)
        # and (https://github.com/Rapptz/discord.py/issues/561)
        # thus it isn't possible to close the aiohttp ClientSession cleanly
        # ...man, I'm getting fed up with some of these design decisions

        for comic in self.comics.values():
            comic.session = self.session

        @aiocron.crontab("*/15 * * * *")
        async def watch_task():
            for name, comic in self.comics.items():
                new_hash = await comic.get_hash()
                old_hash = await self.redis.get(f"comic:hash:{name}")
                if old_hash != new_hash:
                    await self.redis.set(f"comic:hash:{name}", new_hash)
                    for channel_id in \
                            await self.redis.smembers(
                                f"comic:watching:{name}"):
                        channel = self.bot.get_channel(int(channel_id))
                        await self.pack_send(
                            channel, *(await comic.get_post("latest")))

    async def add_watch(self, series, channel_id):
        await self.redis.sadd(f"comic:watching:{series}", channel_id)

    async def rem_watch(self, series, channel_id):
        await self.redis.srem(f"comic:watching:{series}", channel_id)

    async def is_watching(self, series, channel_id):
        return await self.redis.sismember(
            f"comic:watching:{series}", channel_id)

    @commands.command(name="comics")
    async def comics_list(self, ctx):
        "List the comics available"
        embed = discord.Embed(title="Comics available")

        embed.description = "\n".join(
            # ugly hack to get around no \n in f-string
            f"""{name}: {self.comics[name].__doc__.replace('''
''', ' ')}""" for name in self.comics
        )

        await ctx.send(embed=embed)

    @commands.command()
    async def comicswatching(self, ctx):
        "List the Comics currently being watched!"
        watching = []

        for name in self.comics:
            if await self.redis.sismember(
                    f"comic:watching:{name}", ctx.channel.id):
                watching.append(name)

        if ctx.guild:
            name = f"#{ctx.channel.name}"
        else:
            name = f"@{ctx.author.display_name}"
        embed = discord.Embed(title=f"{name} is watching...")
        embed.description = ", ".join(name for name in watching)

        await ctx.send(embed=embed)


comics = {
    "animegirl": animegirl.AnimeGirl(),
    "xkcd": xkcd.XKCD(),
    "testcomic": testcomic.TestComic()
}


def make_command(name, comic):
    @commands.command(name=name, brief=comic.__doc__)
    async def _command(self, ctx, *, number: typing.Optional[str] = "random"):
        if number == "watch":
            if ctx.guild:
                if not ctx.channel.permissions_for(ctx.author).administrator:
                    raise commands.CommandError(
                        "To prevent spam, "
                        "only administrators can watch comics.")
            await self.add_watch(name, ctx.channel.id)
            await ctx.message.add_reaction("✅")
        elif number == "unwatch":
            if ctx.guild:
                if not ctx.channel.permissions_for(ctx.author).administrator:
                    raise commands.CommandError(
                        "To prevent spam, "
                        "only administrators can watch comics.")
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


def setup(bot):
    bot.add_cog(Comics(bot))
