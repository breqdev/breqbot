import time
import os
import random

import discord
from discord.ext import commands

from .items import Item

class Quests(commands.Cog):
    "Look for items!"
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

        self.GET_COINS_INTERVAL = int(os.getenv("GET_COINS_INTERVAL"))
        self.GET_COINS_AMOUNT = int(os.getenv("GET_COINS_AMOUNT"))
        self.GET_ITEM_FREQUENCY = float(os.getenv("GET_ITEM_FREQUENCY"))

    async def config_only(ctx):
        return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
                and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))

    @commands.command()
    async def free(self, ctx):
        "Get free items and coins! Rate limited."
        if ctx.guild is None:
            return

        # Calculate time to wait before collecting
        last_daily = float(self.redis.get(f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}") or 0)
        current_time = time.time()
        time_until = (last_daily + self.GET_COINS_INTERVAL) - current_time

        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            await ctx.send(f"{ctx.author.name}, you must wait **{ftime}** to claim more coins!")
            return

        # Update latest collection
        self.redis.set(f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}", current_time)

        # Give free coins and items
        self.redis.incr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}", self.GET_COINS_AMOUNT)

        item = None

        if random.random() < self.GET_ITEM_FREQUENCY:
            item_uuid = self.redis.srandmember("quests:free:items")
            if item_uuid is not None:
                self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item_uuid)
                item = Item.from_redis(self.redis, item_uuid)

        # Calculate time to wait until next free collection
        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))
        if item is not None:
            await ctx.send(f"{ctx.author.name}, you have claimed **{self.GET_COINS_AMOUNT}** coins and a **{item.name}**! Wait {ftime} to claim more.")
        else:
            await ctx.send(f"{ctx.author.name}, you have claimed **{self.GET_COINS_AMOUNT}** coins! Wait {ftime} to claim more.")

    @commands.command()
    @commands.check(config_only)
    async def list_free(self, ctx):
        "List available free items"
        items = [Item.from_redis(self.redis, uuid) for uuid in self.redis.smembers("quests:free:items")]
        await ctx.send("Items:\n"+"\n".join(item.name for item in items))

    @commands.command()
    @commands.check(config_only)
    async def add_free(self, ctx, item: str):
        "Add a new free item"
        item = Item.from_name(self.redis, item)
        self.redis.sadd("quests:free:items", item.uuid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(config_only)
    async def remove_free(self, ctx, item: str):
        "Remove a free item"
        item = Item.from_name(self.redis, item)
        self.redis.srem("quests:free:items", item.uuid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def quest(self, ctx):
        "Complete a quest!"
        await ctx.send("Sorry, this feature is not available yet.")

def setup(bot):
    bot.add_cog(Quests(bot))
