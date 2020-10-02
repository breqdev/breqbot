import typing

import discord
from discord.ext import commands

from .itemlib import Item, MissingItem, ItemBaseCog
from ..base import UserError


class Items(ItemBaseCog):
    "Manage items! These can be purchased, traded, used, or worn."
    @commands.command()
    @commands.guild_only()
    async def item(self, ctx, item: str):
        "Get information about an item :information_source:"
        item = Item.from_name(self.redis, ctx.guild.id, item)

        embed = discord.Embed()
        embed.title = item.name
        embed.description = item.desc

        embed.add_field(name="Wearable",
                        value=("Yes" if int(item.wearable) else "No"))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
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
                    self.redis.srem(
                        f"items:list:{ctx.guild.id}:{user.id}", uuid)
                else:
                    self.redis.srem(f"items:list:{ctx.guild.id}", uuid)
            else:
                items.append(item)

        embed = discord.Embed(title=f"Items on {ctx.guild.name}")

        embed.description = "\n".join(
            f"• {item.name}: {item.desc}"
            + (" *(wearable)*" if int(item.wearable) else "")
            for item in items)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.check(ItemBaseCog.shopkeeper_only)
    async def makeitem(self, ctx, item: str, desc: str, wearable: int = 0):
        "Create an item"
        if not Item.check_name(self.redis, ctx.guild.id, item):
            raise UserError("Name in use!")

        item = Item(item, ctx.guild.id, ctx.author.id, desc, wearable)
        item.to_redis(self.redis)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def delitem(self, ctx, item: str):
        "Delete an item"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        item.check_owner(ctx.author)
        item.delete(self.redis)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def renameitem(self, ctx, oldname: str, newname: str):
        "Rename an item"
        item = Item.from_name(self.redis, ctx.guild.id, oldname)
        item.check_owner(ctx.author)
        item.rename(self.redis, newname)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def modifyitem(self, ctx, item: str, field: str, value: str):
        "Modify an item"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        item.check_owner(ctx.author)
        if field == "desc":
            item.desc = value
        elif field == "wearable":
            item.wearable = value
        else:
            raise UserError("Invalid field!")
        item.to_redis(self.redis)

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Items(bot))
