import hashlib

import requests

import discord
from discord.ext import commands

from ..base import run_in_executor
from .. import publisher


class Scraper(publisher.PublisherCog):
    "Scrape a website or watch it for changes"
    watch_params = ("url",)
    scan_interval = 1

    @run_in_executor
    def _get_content(self, url):
        return bytes.decode(requests.get(url).content, "utf-8")

    @commands.command()
    async def url(self, ctx, url: str):
        "Return the raw HTML at a URL"

        embed = discord.Embed(title=url)
        embed.description = await self._get_content(url)

        if len(embed.description) > 2000:
            embed.description = "Source too big!"

        await ctx.send(embed=embed)

    async def get_hash(self, url):
        content = await self._get_content(url)
        hash = hashlib.sha1(content.encode("utf-8")).hexdigest()
        return hash

    async def get_update(self, url):
        embed = discord.Embed(title=url)
        embed.description = await self._get_content(url)

        if len(embed.description) > 2000:
            embed.description = "Source too big!"

        return embed, []


def setup(bot):
    bot.add_cog(Scraper(bot))
