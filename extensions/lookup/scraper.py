import discord
from discord.ext import commands

from ..base import BaseCog


class Scraper(BaseCog):
    "Scrape a website or watch it for changes"

    async def _get_content(self, url):
        async with self.session.get(url) as response:
            return await response.text()

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
