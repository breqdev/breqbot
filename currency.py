import os
import time
import typing

import discord
from discord.ext import commands

import redis

class Currency(commands.Cog):
    GET_COINS_INTERVAL = 3600
    GET_COINS_AMOUNT = 10

    def __init__(self, bot):
        self.bot = bot
        self.redis = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

    @commands.command()
    async def balance(self, ctx, user: typing.Optional[discord.User]):
        "Check your current coin balance!"
        if ctx.guild is None:
            return

        if user is None:
            user = ctx.author
        coins = self.redis.get(f"currency:balance:{ctx.guild}:{user.id}")
        if coins is None:
            self.redis.set(f"currency:balance:{ctx.guild}:{user.id}", 0)
            coins = 0
        await ctx.send(f"{user.name} has **{coins}** Breqcoins.")

    @commands.command()
    async def get_coins(self, ctx):
        "Get more money"
        if ctx.guild is None:
            return

        last_daily = float(self.redis.get(f"currency:get_coins:latest:{ctx.guild}:{ctx.author.id}") or 0)
        current_time = time.time()
        time_until = (last_daily + Currency.GET_COINS_INTERVAL) - current_time
        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            await ctx.send(f"{ctx.author.name}, you must wait **{ftime}** to claim more coins!")
            return

        ftime = time.strftime("%H:%M:%S", time.gmtime(Currency.GET_COINS_INTERVAL))

        self.redis.set(f"currency:get_coins:latest:{ctx.guild}:{ctx.author.id}", current_time)
        self.redis.incr(f"currency:balance:{ctx.guild}:{ctx.author.id}", Currency.GET_COINS_AMOUNT)

        await ctx.send(f"{ctx.author.name}, you have claimed **{Currency.GET_COINS_AMOUNT}** coins! Wait {ftime} to claim more.")

def setup(bot):
    bot.add_cog(Currency(bot))
