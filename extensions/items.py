import typing

import discord
from discord.ext import commands

from .utils import *


class Items(BaseCog):
    @commands.command()
    @passfail
    async def item(self, ctx, item: str):
        "Get information about an item :information_source:"
        item = Item.from_name(self.redis, ctx.guild.id, item)

        return (f"{item.name}: {item.desc} "
                f"{'*(wearable)*' if item.wearable else ''}")

    @commands.command()
    @passfail
    async def items(self, ctx, user: typing.Optional[discord.User] = None):
        "Get a list of items, optionally filter by creator :dividers:"
        if user:
            uuids = self.redis.smembers(f"items:list:{ctx.guild.id}:{user.id}")
        else:
            uuids = self.redis.smembers(f"items:list:{ctx.guild.id}")

        items = []
        for uuid in uuids:
            item = Item.from_redis(self.redis, uuid)
            if isinstance(item, MissingItem):
                if user:
                    self.redis.srem(f"items:list:{ctx.guild.id}:{user.id}", uuid)
                else:
                    self.redis.srem(f"items:list:{ctx.guild.id}", uuid)
            else:
                items.append(item)

        return "Items:\n"+"\n".join(str(item) for item in items)

    @commands.command()
    @passfail
    async def makeitem(self, ctx, item: str, desc: str, wearable: int = 0):
        "Create an item"
        if not Item.check_name(self.redis, ctx.guild.id, item):
            Fail("Name in use!")

        item = Item(item, ctx.guild.id, ctx.author.id, desc, wearable)
        item.to_redis(self.redis)

    @commands.command()
    @passfail
    async def delitem(self, ctx, item: str):
        "Delete an item"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        item.check_owner(ctx.author)
        item.delete(self.redis)

    @commands.command()
    @passfail
    async def renameitem(self, ctx, oldname: str, newname: str):
        "Rename an item"
        item = Item.from_name(self.redis, ctx.guild.id, oldname)
        item.check_owner(ctx.author)
        item.rename(self.redis, newname)

    @commands.command()
    @passfail
    async def modifyitem(self, ctx, item: str, field: str, value: str):
        "Modify an item"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        item.check_owner(ctx.author)
        if field == "desc":
            item.desc = value
        elif field == "wearable":
            item.wearable = value
        else:
            raise Fail("Invalid field!")
        item.to_redis(self.redis)

def setup(bot):
    bot.add_cog(Items(bot))
