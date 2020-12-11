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
        self.bot.watches["Comics"] = self.watch

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


comics = {
    "animegirl": animegirl.AnimeGirl(),
    "xkcd": xkcd.XKCD(),
    "testcomic": testcomic.TestComic()
}


def make_command(name, comic):
    @commands.group(name=name, brief=comic.__doc__,
                    invoke_without_command=True)
    async def _command(self, ctx, *, number: typing.Optional[str] = "random"):
        response = await comic.get_post(number)
        await response.send_to(ctx)

    @_command.command(name="watch", brief=f"Get updates for {name}!")
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx):
        await self.watch.register(ctx.channel, name)
        await ctx.message.add_reaction("✅")

    @_command.command(name="unwatch", brief=f"Disable updates for {name}")
    @commands.has_guild_permissions(manage_messages=True)
    async def unwatch(self, ctx):
        await self.watch.unregister(ctx.channel, name)
        await ctx.message.add_reaction("✅")

    return {name: _command, f"{name}_watch": watch, f"{name}_unwatch": unwatch}


new_commands = {}
for name, comic in comics.items():
    # can't wait for py3.9
    new_commands = {**new_commands, **make_command(name, comic)}

Comics = type("Comics", (BaseComics,), new_commands)
Comics.comics = comics


def setup(bot):
    bot.add_cog(Comics(bot))
