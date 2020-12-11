import typing

import discord
from discord.ext import commands

from .. import base
from . import itemlib


class Shop(base.BaseCog):
    "Buy things from the shop!"

    category = "Economy"

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def shop(self, ctx):
        "List items in the shop :shopping_bags:"

        item_uuids = await self.redis.smembers(f"shop:items:{ctx.guild.id}")
        shop_items = {uuid: await itemlib.Item.from_redis(self.redis, uuid)
                      for uuid in item_uuids}
        prices = {}

        missing = []
        for uuid, item in shop_items.items():
            if item.missing:
                missing.append(uuid)
                await self.redis.srem(f"shop:items:{ctx.guild.id}", uuid)

        for uuid in missing:
            await self.redis.delete(f"shop:prices:{ctx.guild.id}:{uuid}")
            del shop_items[uuid]

        for item_uuid in item_uuids:
            prices[item_uuid] = await self.redis.get(
                f"shop:prices:{ctx.guild.id}:{item_uuid}")

        embed = discord.Embed(title=f"Items for sale on {ctx.guild.name}")

        if prices:
            embed.description = "\n".join(
                f"{shop_items[uuid].name}: {prices[uuid]} coins"
                for uuid in shop_items.keys())
        else:
            embed.description = "The shop is empty for now."

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def buy(self, ctx, item: str, amount: typing.Optional[int] = 1):
        "Buy an item from the shop :coin:"

        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)

        price_ea = await self.redis.get(
            f"shop:prices:{ctx.guild.id}:{item.uuid}")
        if price_ea is None:
            raise commands.CommandError("Item is not for sale!")

        price = int(price_ea) * amount

        async with itemlib.Wallet(ctx.author, ctx.guild, self.redis) as wallet:
            await wallet.remove(price)

        async with itemlib.Inventory(ctx.author, ctx.guild, self.redis) \
                as inventory:
            await inventory.add(item, amount)

        await ctx.message.add_reaction("✅")

    @shop.command()
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def list(self, ctx, item: str, price: int):
        "List an item in the shop :new:"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)
        await self.redis.sadd(f"shop:items:{ctx.guild.id}", item.uuid)
        await self.redis.set(f"shop:prices:{ctx.guild.id}:{item.uuid}", price)

        await ctx.message.add_reaction("✅")

    @shop.command()
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def delist(self, ctx, item: str):
        "Remove an item from the shop :no_entry:"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)
        await self.redis.srem(f"shop:items:{ctx.guild.id}", item.uuid)
        await self.redis.delete(f"shop:prices:{ctx.guild.id}:{item.uuid}")

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Shop(bot))
