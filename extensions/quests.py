import time
import os
import json
import random
import asyncio

import discord
from discord.ext import commands

from .utils import *


class Quests(BaseCog):
    "Look for items!"
    def __init__(self, bot):
        super().__init__(bot)

        if os.getenv("BYPASS_FREE_LIMITS"):
            self.GET_COINS_INTERVAL = 1
        else:
            self.GET_COINS_INTERVAL = 3600

        self.GET_COINS_AMOUNT = 10

        with open("extensions/quests.json") as f:
            self.QUEST_MESSAGES = json.load(f)

    async def free_limit(self, ctx):
        # Calculate time to wait before collecting
        last_daily = float(
            self.redis.get("quests:free:latest:{ctx.guild.id}:{ctx.author.id}")
            or 0)
        current_time = time.time()
        time_until = (last_daily + self.GET_COINS_INTERVAL) - current_time

        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            raise Fail(f"{ctx.author.name}, "
                       f"you must wait **{ftime}** to claim more coins!")

        # Update latest collection
        self.redis.set(
            f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}", current_time)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def free(self, ctx):
        "Get free coins! Rate limited. :coin:"

        await self.free_limit(ctx)

        # Give free coins and items
        self.redis.incr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}",
                        self.GET_COINS_AMOUNT)

        # Calculate time to wait until next free collection
        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))

        return (f"{ctx.author.name}, you have claimed "
                f"**{self.GET_COINS_AMOUNT}** coins! "
                f"Wait {ftime} to claim more.")

    @commands.command()
    @commands.guild_only()
    @passfail
    async def quest(self, ctx):
        "Complete a quest :medal:"

        await self.free_limit(ctx)

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        scenario = random.choice(self.QUEST_MESSAGES)

        embed = discord.Embed(title=f"Quest: {scenario['name']}:")
        embed.add_field(
            name=scenario["prompt"],
            value="\n".join(f"{emojis[idx]}: {choice}"
                            for idx, choice in enumerate(scenario["choices"])))
        message = await ctx.send(embed=embed)
        for emoji in emojis:
            await message.add_reaction(emoji)

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id == ctx.author.id)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=60, check=check)
            except asyncio.TimeoutError:
                return NoReact  # don't do anything
            if reaction.emoji in emojis:
                break
            else:
                await reaction.remove(user)

        choice = scenario["choices"][emojis.index(reaction.emoji)]

        result = random.choice(("large", "medium", "small"))

        coin_multipliers = {"large": 2, "medium": 1, "small": 0.2}

        coins = int(coin_multipliers[result] * self.GET_COINS_AMOUNT)
        message = scenario[result].format(coins=coins, choice=choice)

        self.redis.incr(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", coins)

        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))
        message += f"\nWait {ftime} to play again!"
        return message


def setup(bot):
    bot.add_cog(Quests(bot))
