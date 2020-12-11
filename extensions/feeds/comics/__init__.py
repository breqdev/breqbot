import typing

import aiohttp
import discord
from discord.ext import commands

from ... import base
from ... import watch

from . import animegirl, xkcd, testcomic


class BaseComics(base.BaseCog, watch.Watchable):

    description = "View a variety of cool comics!"
    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()

        for comic in self.comics.values():
            comic.session = self.session

        self.watch = watch.ChannelWatch(self, crontab="*/15 * * * *")

    async def get_state(self, target):
        if target not in self.comics:
            return None
        return self.comics[target]

    async def get_hash(self, state):
        return await state.get_hash()

    async def get_response(self, state):
        return await state.get_post("latest")

    async def check_target(self, target):
        return target in self.comics

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

        watching = await self.watch.get_targets(ctx.channel)

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
            await self.watch.register(ctx.channel, name)
            await ctx.message.add_reaction("✅")
        elif number == "unwatch":
            if ctx.guild:
                if not ctx.channel.permissions_for(ctx.author).administrator:
                    raise commands.CommandError(
                        "To prevent spam, "
                        "only administrators can watch comics.")
            await self.watch.unregister(ctx.channel, name)
            await ctx.message.add_reaction("✅")
        elif number == "watching":
            if await self.watch.is_registered(ctx.channel, name):
                await ctx.send(
                    f"{ctx.channel.mention} is currently watching {name}.")
            else:
                await ctx.send(
                    f"{ctx.channel.mention} is not currently watching {name}.")
        else:
            response = await comic.get_post(number)
            await response.send_to(ctx)

    return _command


new_commands = {}
for name, comic in comics.items():
    new_commands[name] = make_command(name, comic)

Comics = type("Comics", (BaseComics,), new_commands)
Comics.comics = comics


def setup(bot):
    bot.add_cog(Comics(bot))
