import time
import os
import json
import random
import asyncio

import discord
from discord.ext import commands

from .itemlib import ItemBaseCog


class QuestsError(commands.UserInputError):
    pass


class Quests(ItemBaseCog):
    "Look for items!"
    def __init__(self, bot):
        super().__init__(bot)

        if int(os.getenv("BYPASS_FREE_LIMITS")):
            self.GET_COINS_INTERVAL = 1
        else:
            self.GET_COINS_INTERVAL = 3600

        self.GET_COINS_AMOUNT = 10

        with open("extensions/economy/quests.json") as f:
            self.QUEST_MESSAGES = json.load(f)

    async def free_limit(self, ctx):
        # Calculate time to wait before collecting
        last_daily = float(
            self.redis.get(
                f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}") or 0)
        current_time = time.time()
        time_until = (last_daily + self.GET_COINS_INTERVAL) - current_time

        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            raise QuestsError(f"{ctx.author.display_name}, you must wait "
                              f"**{ftime}** to claim more coins!")

        # Update latest collection
        self.redis.set(
            f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}", current_time)

    @commands.command()
    @commands.guild_only()
    async def free(self, ctx):
        "Get free coins! Rate limited. :coin:"

        await self.free_limit(ctx)

        # Give free coins and items
        self.redis.incr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}",
                        self.GET_COINS_AMOUNT)

        # Calculate time to wait until next free collection
        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))

        await ctx.send(f"{ctx.author.display_name}, you have claimed "
                       f"**{self.GET_COINS_AMOUNT}** coins! "
                       f"Wait {ftime} to claim more.")

    @commands.command()
    @commands.guild_only()
    async def quest(self, ctx):
        "Complete a quest :medal:"

        await self.free_limit(ctx)

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        scenario = random.choice(self.QUEST_MESSAGES)

        embed = discord.Embed(title=f"Quest: {scenario['name']}:")
        embed.description = (
            f"{scenario['prompt']}\n\n"
            + "\n".join(f"{emojis[idx]}: {choice}"
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
                return
            if reaction.emoji in emojis:
                break
            else:
                await reaction.remove(user)

        await message.clear_reactions()

        choice = scenario["choices"][emojis.index(reaction.emoji)]

        result = random.choice(("large", "medium", "small"))

        coin_multipliers = {"large": 2, "medium": 1, "small": 0.2}

        coins = int(coin_multipliers[result] * self.GET_COINS_AMOUNT)
        result = scenario[result].format(coins=coins, choice=choice)

        self.redis.incr(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", coins)

        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))
        result += f"\nWait {ftime} to play again!"

        embed.description += "\n\n" + result
        await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Quests(bot))
