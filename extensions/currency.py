import typing

import discord
from discord.ext import commands

from .utils import *


class Currency(BaseCog):
    "Earn and spend Breqcoins!"

    @commands.command()
    @commands.guild_only()
    @passfail
    async def balance(self, ctx, user: typing.Optional[discord.User]):
        "Check your current coin balance :moneybag:"
        if user is None:
            user = ctx.author
        coins = self.redis.get(f"currency:balance:{ctx.guild.id}:{user.id}")
        if coins is None:
            self.redis.set(f"currency:balance:{ctx.guild.id}:{user.id}", 0)
            coins = 0
        return f"{user.name} has **{coins}** Breqcoins."

    @commands.command()
    @commands.guild_only()
    @passfail
    async def givecoins(self, ctx, user: discord.User, amount: int):
        "Give coins to another user :incoming_envelope:"
        balance = self.redis.get(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}")

        if int(balance) < amount:
            raise Fail("Not enough coins!")
            return

        self.redis.decr(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", amount)
        self.redis.incr(f"currency:balance:{ctx.guild.id}:{user.id}", amount)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def shop(self, ctx):
        "List items in the shop :shopping_bags:"

        item_uuids = self.redis.smembers(f"shop:items:{ctx.guild.id}")
        shop_items = {uuid: Item.from_redis(self.redis, uuid)
                      for uuid in item_uuids}
        prices = {}

        missing = []
        for uuid, item in shop_items.items():
            if isinstance(item, MissingItem):
                missing.append(uuid)
                self.redis.srem(f"shop:items:{ctx.guild.id}", uuid)

        for uuid in missing:
            self.redis.delete(f"shop:prices:{ctx.guild.id}:{item_uuid}")
            del shop_items[uuid]

        for item_uuid in item_uuids:
            prices[item_uuid] = self.redis.get(
                f"shop:prices:{ctx.guild.id}:{item_uuid}")

        embed = discord.Embed(title=f"Items for sale on {ctx.guild.name}")

        if prices:
            embed.description = "\n".join(
                f"{shop_items[uuid].name}: {prices[uuid]} coins"
                for uuid in shop_items.keys())
        else:
            embed.description = "The shop is empty for now."

        return embed

    @commands.command()
    @commands.guild_only()
    @passfail
    async def buy(self, ctx, item: str, amount: typing.Optional[int] = 1):
        "Buy an item from the shop :coin:"

        item = self.get_item(item)

        price_ea = self.redis.get(f"shop:prices:{ctx.guild.id}:{item.uuid}")
        if price_ea is None:
            raise Fail("Item is not for sale!")

        price = int(price_ea) * amount
        balance = int(self.redis.get(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}") or 0)

        if balance < price:
            raise Fail("Not enough coins!")

        self.redis.decr(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", price)
        self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, amount)

    @commands.command()
    @commands.check(shopkeeper_only)
    @passfail
    async def list(self, ctx, item: str, price: int):
        "List an item in the shop :new:"
        item = self.get_item(item)
        self.redis.sadd(f"shop:items:{ctx.guild.id}", item.uuid)
        self.redis.set(f"shop:prices:{ctx.guild.id}:{item.uuid}", price)

    @commands.command()
    @commands.check(shopkeeper_only)
    @passfail
    async def delist(self, ctx, item: str):
        "Remove an item from the shop :no_entry:"
        item = self.get_item(item)
        self.redis.srem(f"shop:items:{ctx.guild.id}", item.uuid)
        self.redis.delete(f"shop:prices:{ctx.guild.id}:{item.uuid}")


def setup(bot):
    bot.add_cog(Currency(bot))
