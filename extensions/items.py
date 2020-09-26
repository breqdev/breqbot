import discord
from discord.ext import commands

from .utils import *


class Items(BaseCog):
    @commands.command()
    @passfail
    async def item(self, ctx, item: str):
        "Get information about an item :information_source:"
        item = self.get_item(item)

        return (f"{item.name}: {item.desc} "
                f"{'*(wearable)*' if item.wearable else ''}")


def setup(bot):
    bot.add_cog(Items(bot))
