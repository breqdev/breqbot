import typing

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

    @commands.command()
    @passfail
    async def items(self, ctx, user: typing.Optional[discord.User]):
        "Get a list of items, optionally filter by creator :dividers:"
        return "Items:\n"+"\n".join(
            str(Item.from_redis(self.redis, uuid))
            for uuid in self.redis.smembers("items:list"))

    @commands.command()
    @passfail
    async def makeitem(self, ctx, item: str, desc: str, wearable: int = 0):
        "Create an item"
        if not Item.check_name(self.redis, item):
            Fail("Name in use!")

        item = Item(item, desc, wearable)
        item.to_redis(self.redis)

    @commands.command()
    @passfail
    async def delitem(self, ctx, item: str):
        "Delete an item"
        item = self.get_item(item)
        item.delete(self.redis)

    @commands.command()
    @passfail
    async def renameitem(self, ctx, oldname: str, newname: str):
        "Rename an item"
        item = self.get_item(oldname)
        item.rename(self.redis, newname)

    @commands.command()
    @passfail
    async def modifyitem(self, ctx, item: str, field: str, value: str):
        "Modify an item"
        item = Item.from_name(self.redis, item)
        if field == "desc":
            item.desc = value
        elif field == "wearable":
            item.wearable = value
        else:
            raise Fail("Invalid field!")
        item.to_redis(self.redis)

def setup(bot):
    bot.add_cog(Items(bot))
