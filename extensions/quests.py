import time
import os
import random
import asyncio

import discord
from discord.ext import commands

from .items import Item
from .utils import *

class Quests(BaseCog):
    "Look for items!"
    def __init__(self, bot):
        super().__init__(bot)

        self.GET_COINS_INTERVAL = int(os.getenv("GET_COINS_INTERVAL"))
        self.GET_COINS_AMOUNT = int(os.getenv("GET_COINS_AMOUNT"))
        self.GET_ITEM_FREQUENCY = float(os.getenv("GET_ITEM_FREQUENCY"))

    async def free_limit(self, ctx):
        # Calculate time to wait before collecting
        last_daily = float(self.redis.get(f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}") or 0)
        current_time = time.time()
        time_until = (last_daily + self.GET_COINS_INTERVAL) - current_time

        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            raise Fail(f"{ctx.author.name}, you must wait **{ftime}** to claim more coins!")

        # Update latest collection
        self.redis.set(f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}", current_time)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def free(self, ctx):
        "Get free items and coins! Rate limited."

        await self.free_limit(ctx)

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
            return f"{ctx.author.name}, you have claimed **{self.GET_COINS_AMOUNT}** coins and a **{item.name}**! Wait {ftime} to claim more."
        else:
            return f"{ctx.author.name}, you have claimed **{self.GET_COINS_AMOUNT}** coins! Wait {ftime} to claim more."

    @commands.command()
    @commands.check(config_only)
    @passfail
    async def list_free(self, ctx):
        "List available free items"
        items = [Item.from_redis(self.redis, uuid) for uuid in self.redis.smembers("quests:free:items")]
        return "Items:\n"+"\n".join(item.name for item in items)

    @commands.command()
    @commands.check(config_only)
    @passfail
    async def add_free(self, ctx, item: str):
        "Add a new free item"
        item = self.get_item(item)
        self.redis.sadd("quests:free:items", item.uuid)

    @commands.command()
    @commands.check(config_only)
    @passfail
    async def remove_free(self, ctx, item: str):
        "Remove a free item"
        item = self.get_item(item)
        self.redis.srem("quests:free:items", item.uuid)

    QUEST_MESSAGES = [
        {
            "name": "Dig for treasure",
            "prompt": "You have a shovel and some treasure maps. Choose a site to dig",
            "choices": ["under the tree", "in the desert", "on the beach", "by the railroad"],
            "large": "You found a treasure chest {choice}! Collect **{coins} coins.**",
            "medium": "You found some gold {choice}! Collect **{coins} coins.**",
            "small": "All you found was a shiny rock. Collect **{coins} coins.**"
        },
        {
            "name": "Invest in cryptocurrency",
            "prompt": "You won free cryptocurrency! Choose a coin",
            "choices": ["DokiCoin", "CuffCoin", "DubstepCoin", "MemeCoin"],
            "large": "{choice} went to the moon! Collect **{coins} coins.**",
            "medium": "{choice} held steady. Collect **{coins} coins.**",
            "small": "{choice} crashed. Collect **{coins} coins.**"
        },
    ]

    @commands.command()
    @commands.guild_only()
    @passfail
    async def quest(self, ctx):
        "Complete a quest!"

        await self.free_limit(ctx)

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
        scenario = random.choice(self.QUEST_MESSAGES)

        embed = discord.Embed(title=f"Quest: {scenario['name']}:")
        embed.add_field(name=scenario["prompt"],
                        value="\n".join(f"{emojis[idx]}: {choice}"
                                        for idx, choice in enumerate(scenario["choices"])))
        message = await ctx.send(embed=embed)
        for emoji in emojis:
            await message.add_reaction(emoji)

        def check(reaction, user):
            return reaction.message.id == message.id and user.id == ctx.author.id

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)
            except asyncio.TimeoutError:
                return NoReact # don't do anything
            if reaction.emoji in emojis:
                break
            else:
                await reaction.remove(user)

        choice = scenario["choices"][emojis.index(reaction.emoji)]

        result = random.choice(("large", "medium", "small"))

        coin_multipliers = {"large": 2, "medium": 1, "small": 0.2}

        coins = int(coin_multipliers[result] * self.GET_COINS_AMOUNT)
        message = scenario[result].format(coins=coins, choice=choice)

        self.redis.incr(f"currency:balance:{ctx.guild.id}:{ctx.author.id}", coins)

        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))
        message += f"\nWait {ftime} to play again!"
        return message


def setup(bot):
    bot.add_cog(Quests(bot))
