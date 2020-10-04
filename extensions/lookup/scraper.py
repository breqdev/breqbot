import requests

import discord
from discord.ext import commands

from ..base import BaseCog, run_in_executor


class Scraper(BaseCog):
    "Scrape a website or watch it for changes"

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


def setup(bot):
    bot.add_cog(Scraper(bot))
