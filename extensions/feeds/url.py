import aiohttp
import discord
from discord.ext import commands

from .. import base
from .. import watch


class URL(base.BaseCog, watch.Watchable, command_attrs=dict(hidden=True)):
    "Retrieve or watch a URL"

    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)

        self.session = aiohttp.ClientSession()

        self.watch = watch.MessageWatch(self)

    @commands.command()
    async def url(self, ctx, *, url: str):
        "Fetch a URL"

        try:
            async with self.session.get(url) as response:
                text = await response.text()
        except aiohttp.InvalidURL:
            raise commands.CommandError("Invalid URL!")

        embed = discord.Embed(title=url)
        embed.description = text[:200]

        await ctx.send(embed=embed)

    @commands.command()
    async def urlwatch(self, ctx, *, url: str):
        "Watch a URL"
        await self.watch.register(ctx.channel, url)

    async def get_state(self, target):
        try:
            async with self.session.get(target) as response:
                data = await response.text()
        except aiohttp.ClientError:
            data = "Inaccessible"

        return {"url": target, "data": data}

    async def get_pack(self, state):
        embed = discord.Embed(title=state["url"])
        embed.description = state["data"][:200]

        return "", [], embed


def setup(bot):
    bot.add_cog(URL(bot))
