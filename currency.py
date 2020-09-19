import os
import time
import typing

import discord
from discord.ext import commands

from items import Item

class Currency(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

        self.GET_COINS_INTERVAL = int(os.getenv("GET_COINS_INTERVAL")) or 3600
        self.GET_COINS_AMOUNT = 10

    async def shopkeeper_only(ctx):
        if ctx.author.id == int(os.getenv("MAIN_SHOPKEEPER")):
            return True
        for role in ctx.author.roles:
            if role.name == "Shopkeeper":
                return True
        return False

    @commands.command()
    async def balance(self, ctx, user: typing.Optional[discord.User]):
        "Check your current coin balance"
        if ctx.guild is None:
            return

        if user is None:
            user = ctx.author
        coins = self.redis.get(f"currency:balance:{ctx.guild.id}:{user.id}")
        if coins is None:
            self.redis.set(f"currency:balance:{ctx.guild.id}:{user.id}", 0)
            coins = 0
        await ctx.send(f"{user.name} has **{coins}** Breqcoins.")

    @commands.command()
    async def get_coins(self, ctx):
        "Get more coins! 10 coins per hour."
        if ctx.guild is None:
            return

        last_daily = float(self.redis.get(f"currency:get_coins:latest:{ctx.guild.id}:{ctx.author.id}") or 0)
        current_time = time.time()
        time_until = (last_daily + self.GET_COINS_INTERVAL) - current_time
        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            await ctx.send(f"{ctx.author.name}, you must wait **{ftime}** to claim more coins!")
            return

        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))

        self.redis.set(f"currency:get_coins:latest:{ctx.guild.id}:{ctx.author.id}", current_time)
        self.redis.incr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}", self.GET_COINS_AMOUNT)

        await ctx.send(f"{ctx.author.name}, you have claimed **{self.GET_COINS_AMOUNT}** coins! Wait {ftime} to claim more.")

    @commands.command()
    async def give_coins(self, ctx, user: discord.User, amount: int):
        "Give coins to another user"
        balance = self.redis.get(f"currency:balance:{ctx.guild.id}:{ctx.author.id}")

        if int(balance) < amount:
            await ctx.send("Not enough coins!")
            return

        self.redis.decr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}", amount)
        self.redis.incr(f"currency:balance:{ctx.guild.id}:{user.id}", amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def shop(self, ctx):
        "List items in the shop!"

        item_uuids = self.redis.smembers(f"shop:items:{ctx.guild.id}")
        shop_items = {uuid: Item.from_redis(self.redis, uuid) for uuid in item_uuids}
        prices = {}

        for item_uuid in item_uuids:
            prices[item_uuid] = self.redis.get(f"shop:prices:{ctx.guild.id}:{item_uuid}")

        if prices:
            await ctx.send(f"Items for sale on {ctx.guild.name}:\n"
                           + "\n".join(f"{shop_items[uuid].name}: {prices[uuid]} coins\n"
                                       for uuid in shop_items.keys()))
        else:
            await ctx.send(f"The shop on {ctx.guild.name} is empty!")

    @commands.command()
    async def buy(self, ctx, item: str, amount: typing.Optional[int] = 1):
        "Buy an item from the shop"

        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        price_ea = self.redis.get(f"shop:prices:{ctx.guild.id}:{item.uuid}")
        if price_ea is None:
            await ctx.send("Item is not for sale!")
            return

        price = int(price_ea) * amount
        balance = int(self.redis.get(f"currency:balance:{ctx.guild.id}:{ctx.author.id}") or 0)

        if balance < price:
            await ctx.send("Not enough coins!")
            return

        self.redis.decr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}", price)
        self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(shopkeeper_only)
    async def list(self, ctx, item: str, price: int):
        "List an item in the shop"

        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        self.redis.sadd(f"shop:items:{ctx.guild.id}", item.uuid)
        self.redis.set(f"shop:prices:{ctx.guild.id}:{item.uuid}", price)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(shopkeeper_only)
    async def delist(self, ctx, item: str):
        "Remove an item from the shop"

        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        self.redis.srem(f"shop:items:{ctx.guild.id}", item.uuid)
        self.redis.delete(f"shop:prices:{ctx.guild.id}:{item.uuid}")
        await ctx.message.add_reaction("✅")

def setup(bot):
    bot.add_cog(Currency(bot))
