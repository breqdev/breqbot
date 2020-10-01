import typing
import random
import asyncio

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
        return f"{user.display_name} has **{coins}** Breqcoins."

    @commands.command()
    @commands.guild_only()
    @passfail
    async def pay(self, ctx, user: discord.User, amount: int):
        "Give coins to another user :incoming_envelope:"
        balance = self.redis.get(
            f"currency:balance:{ctx.guild.id}:{ctx.author.id}") or "0"

        if amount < 0:
            raise Fail(f"Nice try {ctx.author.mention}, you cannot steal coins.")

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

        item = Item.from_name(self.redis, ctx.guild.id, item)

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
    @commands.guild_only()
    @commands.check(shopkeeper_only)
    @passfail
    async def list(self, ctx, item: str, price: int):
        "List an item in the shop :new:"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        self.redis.sadd(f"shop:items:{ctx.guild.id}", item.uuid)
        self.redis.set(f"shop:prices:{ctx.guild.id}:{item.uuid}", price)

    @commands.command()
    @commands.guild_only()
    @commands.check(shopkeeper_only)
    @passfail
    async def delist(self, ctx, item: str):
        "Remove an item from the shop :no_entry:"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        self.redis.srem(f"shop:items:{ctx.guild.id}", item.uuid)
        self.redis.delete(f"shop:prices:{ctx.guild.id}:{item.uuid}")

    @commands.command()
    @commands.guild_only()
    @passfail
    async def roulette(self, ctx, wager: int):
        "Gamble coins - will you earn more, or lose them all?"

        embed = discord.Embed(title=f"Roulette ({wager} coins)")
        embed.description = "Choose a reaction to place your bet!\nCloses in 10 seconds..."

        message = await ctx.send(embed=embed)

        bet_types = ["🟥", "⬛", "🟩", "🇪", "🇴", "🇭", "🇱"]
        for bet in bet_types:
            await message.add_reaction(bet)

        # Now get the actual message, not just the cached one, so we can view reactions
        message = await ctx.fetch_message(message.id)

        await asyncio.sleep(10)

        wheel = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]

        red = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        black = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

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
        embed.description += f"**{ball}** | {color} | {parity_name.get(parity)} | {range_name.get(range)}\nResults:\n"

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

                balance = int(self.redis.get(f"currency:balance:{ctx.guild.id}:{user.id}") or "0")

                if balance < wager:
                    await reaction.remove(user)
                    continue

                net_winnings = payout - wager
                self.redis.incr(f"currency:balance:{ctx.guild.id}:{user.id}", net_winnings)
                results.append(f"• {user.display_name} {'won' if net_winnings >= 0 else 'lost'} {abs(net_winnings)} coins")

        embed.description += "\n".join(results)

        await message.edit(embed=embed)
        return NoReact


def setup(bot):
    bot.add_cog(Currency(bot))
