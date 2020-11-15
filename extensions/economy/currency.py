import typing
import random
import asyncio
import os
import json
import time

import discord
from discord.ext import commands

from ..base import FuzzyMember
from .itemlib import Item, MissingItem, EconomyCog


class Currency(EconomyCog):
    "Earn and spend Breqcoins!"
    def __init__(self, bot):
        super().__init__(bot)

        if int(os.getenv("BYPASS_FREE_LIMITS")):
            self.GET_COINS_INTERVAL = 1
        else:
            self.GET_COINS_INTERVAL = 3600

        self.GET_COINS_AMOUNT = 10

        with open("extensions/economy/quests.json") as f:
            self.QUEST_MESSAGES = json.load(f)

    @commands.command()
    @commands.guild_only()
    async def balance(self, ctx, user: typing.Optional[FuzzyMember]):
        "Check your current coin balance :moneybag:"
        if user is None:
            user = ctx.author
        coins = await self.redis.get(
            f"currency:balance:{ctx.guild.id}:{user.id}")
        if coins is None:
            await self.redis.set(
                f"currency:balance:{ctx.guild.id}:{user.id}", 0)
            coins = 0
        await ctx.send(f"{user.display_name} has **{coins}** Breqcoins.")

    @commands.command()
    @commands.guild_only()
    async def richest(self, ctx):
        "Display the richest members on the server :moneybag:"
        richest = []

        for member_id in \
                await self.redis.smembers(f"guild:member:{ctx.guild.id}"):
            richest.append((
                ctx.guild.get_member(int(member_id)),
                int(await self.redis.get(
                    f"currency:balance:{ctx.guild.id}:{member_id}")
                    or "0")
            ))

        richest = sorted(richest, key=lambda item: item[1], reverse=True)[:5]

        embed = discord.Embed(title=f"Richest members on {ctx.guild.name}")

        embed.description = "\n".join(
            f"{member.display_name}: {balance}"
            for member, balance in richest if member)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def pay(self, ctx, user: discord.User, amount: int):
        "Give coins to another user :incoming_envelope:"
        balance = await self.redis.get(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}") or "0"

        if amount < 0:
            raise commands.UserInputError(
                f"Nice try {ctx.author.mention}, you cannot steal coins.")

        if int(balance) < amount:
            raise commands.UserInputError("Not enough coins!")
            return

        await self.redis.decrby(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", amount)
        await self.redis.incrby(
            f"currency:balance:{ctx.guild.id}:{user.id}", amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def shop(self, ctx):
        "List items in the shop :shopping_bags:"

        item_uuids = await self.redis.smembers(f"shop:items:{ctx.guild.id}")
        shop_items = {uuid: await Item.from_redis(self.redis, uuid)
                      for uuid in item_uuids}
        prices = {}

        missing = []
        for uuid, item in shop_items.items():
            if isinstance(item, MissingItem):
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

        item = await Item.from_name(self.redis, ctx.guild.id, item)

        price_ea = await self.redis.get(
            f"shop:prices:{ctx.guild.id}:{item.uuid}")
        if price_ea is None:
            raise commands.UserInputError("Item is not for sale!")

        price = int(price_ea) * amount
        balance = int(await self.redis.get(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}") or 0)

        if balance < price:
            raise commands.UserInputError("Not enough coins!")

        await self.redis.decrby(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", price)
        await self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    @commands.check(EconomyCog.shopkeeper_only)
    async def list(self, ctx, item: str, price: int):
        "List an item in the shop :new:"
        item = await Item.from_name(self.redis, ctx.guild.id, item)
        await self.redis.sadd(f"shop:items:{ctx.guild.id}", item.uuid)
        await self.redis.set(f"shop:prices:{ctx.guild.id}:{item.uuid}", price)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    @commands.check(EconomyCog.shopkeeper_only)
    async def delist(self, ctx, item: str):
        "Remove an item from the shop :no_entry:"
        item = await Item.from_name(self.redis, ctx.guild.id, item)
        await self.redis.srem(f"shop:items:{ctx.guild.id}", item.uuid)
        await self.redis.delete(f"shop:prices:{ctx.guild.id}:{item.uuid}")

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def roulette(self, ctx, wager: int):
        "Gamble coins - will you earn more, or lose them all?"

        embed = discord.Embed(title=f"Roulette ({wager} coins)")
        embed.description = ("Choose a reaction to place your bet!\n"
                             "Closes in 10 seconds...")

        message = await ctx.send(embed=embed)

        bet_types = ["🟥", "⬛", "🟩", "🇪", "🇴", "🇭", "🇱"]
        for bet in bet_types:
            await message.add_reaction(bet)

        # Now get the actual message, not just the cached one
        # so we can view reactions
        message = await ctx.fetch_message(message.id)

        await asyncio.sleep(10)

        wheel = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8,
                 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28,
                 12, 35, 3, 26]

        red = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19,
               21, 23, 25, 27, 30, 32, 34, 36]
        black = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20,
                 22, 24, 26, 28, 29, 31, 33, 35]

        ball = random.choice(wheel)
        color = "🟥" if ball in red else "⬛" if ball in black else "🟩"
        parity = None if ball == 0 else "🇪" if ball % 2 == 0 else "🇴"
        range = "🇭" if ball >= 19 else "🇱" if ball >= 1 else None

        parity_name = {
            "🇪": "Even",
            "🇴": "Odd"
        }

        range_name = {
            "🇭": "High",
            "🇱": "Low"
        }

        embed.description = "The wheel has spun! Result:\n"
        embed.description += (f"**{ball}** | {color} | "
                              f"{parity_name.get(parity)} | "
                              f"{range_name.get(range)}\nResults:\n")

        results = []

        for reaction in message.reactions:
            if reaction.emoji not in bet_types:
                await reaction.clear()
                continue

            if reaction.emoji == "🟩" and color == "🟩":
                payout = 36 * wager
            elif reaction.emoji in (color, parity, range):
                payout = 2 * wager
            else:
                payout = 0

            async for user in reaction.users():
                if user.id == self.bot.user.id:
                    continue

                balance = int(
                    await self.redis.get(
                        f"currency:balance:{ctx.guild.id}:{user.id}") or "0")

                if balance < wager:
                    await reaction.remove(user)
                    continue

                net_winnings = payout - wager
                await self.redis.incrby(
                    f"currency:balance:{ctx.guild.id}:{user.id}", net_winnings)
                results.append(f"• {user.display_name} "
                               f"{'won' if net_winnings >= 0 else 'lost'} "
                               f"{abs(net_winnings)} coins")

        embed.description += "\n".join(results)

        await message.edit(embed=embed)

    async def free_limit(self, ctx):
        # Calculate time to wait before collecting
        last_daily = float(
            await self.redis.get(
                f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}") or 0)
        current_time = time.time()
        time_until = (last_daily + self.GET_COINS_INTERVAL) - current_time

        if time_until > 0:
            ftime = time.strftime("%H:%M:%S", time.gmtime(time_until))
            raise commands.UserInputError(
                f"{ctx.author.display_name}, you must wait "
                f"**{ftime}** to claim more coins!")

        # Update latest collection
        await self.redis.set(
            f"quests:free:latest:{ctx.guild.id}:{ctx.author.id}", current_time)

    @commands.command()
    @commands.guild_only()
    async def free(self, ctx):
        "Get free coins! Rate limited. :coin:"

        await self.free_limit(ctx)

        # Give free coins and items
        await self.redis.incrby(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}",
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

        await self.redis.incrby(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}", coins)

        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))
        result += f"\nWait {ftime} to play again!"

        embed.description += "\n\n" + result
        await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Currency(bot))
