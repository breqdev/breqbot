import typing
import random
import asyncio
import os
import json
import time

import discord
from discord.ext import commands

from bot import base
from . import itemlib


class Currency(base.BaseCog):
    "Earn and spend Breqcoins!"

    category = "Economy"

    def __init__(self, bot):
        super().__init__(bot)

        if int(os.getenv("BYPASS_FREE_LIMITS")):
            self.GET_COINS_INTERVAL = 1
        else:
            self.GET_COINS_INTERVAL = 3600

        self.GET_COINS_AMOUNT = 10

        with open("bot/economy/quests.json") as f:
            self.QUEST_MESSAGES = json.load(f)

    @commands.command()
    @commands.guild_only()
    async def balance(self, ctx, user: typing.Optional[base.FuzzyMember]):
        "Check your current coin balance :moneybag:"
        if user is None:
            user = ctx.author

        async with itemlib.Wallet(user, ctx.guild, self.redis) as wallet:
            coins = await wallet.get_balance()

        await ctx.send(f"{user.display_name} has **{coins}** Breqcoins.")

    @commands.command()
    @commands.guild_only()
    async def richest(self, ctx):
        "Display the richest members on the server :moneybag:"
        richest = []

        for member_id in \
                await self.redis.smembers(f"guild:member:{ctx.guild.id}"):

            async with itemlib.Wallet(member_id, ctx.guild, self.redis) \
                    as wallet:
                coins = await wallet.get_balance()

            richest.append((ctx.guild.get_member(int(member_id)), coins))

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

        async with itemlib.Wallet(ctx.author, ctx.guild, self.redis) as wallet:
            await wallet.remove(amount)

        async with itemlib.Wallet(user, ctx.guild, self.redis) as wallet:
            await wallet.add(amount)

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
                try:
                    await reaction.clear()
                except discord.errors.Forbidden:
                    pass
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

                async with itemlib.Wallet(user, ctx.guild, self.redis) \
                        as wallet:
                    try:
                        await wallet.ensure(wager)
                    except commands.CommandError:
                        try:
                            await reaction.remove(user)
                        except discord.errors.Forbidden:
                            pass
                    else:
                        net_winnings = payout - wager
                        if net_winnings >= 0:
                            await wallet.add(net_winnings)
                            results.append(
                                f"• {user.display_name} won "
                                f"{net_winnings} coins")
                        else:
                            await wallet.remove(-net_winnings)
                            results.append(
                                f"• {user.display_name} lost "
                                f"{-net_winnings} coins")

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
            raise commands.CommandError(
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
        async with itemlib.Wallet(ctx.author, ctx.guild, self.redis) as wallet:
            await wallet.add(self.GET_COINS_AMOUNT)

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
                try:
                    await reaction.remove(user)
                except discord.errors.Forbidden:
                    pass

        try:
            await message.clear_reactions()
        except discord.errors.Forbidden:
            pass

        choice = scenario["choices"][emojis.index(reaction.emoji)]

        result = random.choice(("large", "medium", "small"))

        coin_multipliers = {"large": 2, "medium": 1, "small": 0.2}

        coins = int(coin_multipliers[result] * self.GET_COINS_AMOUNT)
        result = scenario[result].format(coins=coins, choice=choice)

        async with itemlib.Wallet(ctx.author, ctx.guild, self.redis) as wallet:
            await wallet.add(coins)

        ftime = time.strftime("%H:%M:%S", time.gmtime(self.GET_COINS_INTERVAL))
        result += f"\nWait {ftime} to play again!"

        embed.description += "\n\n" + result
        await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Currency(bot))
