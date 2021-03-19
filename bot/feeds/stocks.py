import os

import discord
from discord.ext import commands

import aiohttp

from bot import base
from bot import watch


class Stocks(base.BaseCog, watch.Watchable):
    "Watch stock prices"

    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)

        self.session = aiohttp.ClientSession()
        self.key = os.getenv("ALPHA_VANTAGE_API_KEY")

        self.watch = watch.MessageWatch(self, "*/5 * * * *")
        self.bot.watches["Stocks"] = self.watch

    async def get_stock_name(self, ticker):
        async with self.session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "SYMBOL_SEARCH",
                    "keywords": ticker,
                    "apikey": self.key
                }) as response:
            return (await response.json())["bestMatches"][0]["2. name"]

    async def check_target(self, ticker):
        try:
            await self.get_state(ticker)
        except commands.CommandError:
            return False
        else:
            return True

    async def get_state(self, ticker):
        ticker = ticker.upper()
        async with self.session.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": ticker,
                    "apikey": self.key
                }) as response:
            state = (await response.json())["Global Quote"]

        if state:
            return {
                "ticker": ticker,
                "name": await self.get_stock_name(ticker),
                "type": "stock",
                "price": float(state["05. price"])
            }

        raise commands.CommandError("Invalid ticker name")

    async def get_hash(self, state):
        return state["price"]

    async def get_response(self, state):
        embed = discord.Embed(title=f"**{state['ticker']}** ({state['name']})")
        embed.add_field(name="Price", value=state["price"])

        return base.Response(None, {}, embed)

    @commands.group(invoke_without_command=True)
    async def stock(self, ctx, ticker: str):
        "Look up stocks info"

        response = await self.get_response(await self.get_state(ticker))
        await response.send_to(ctx)

    @stock.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx, ticker: str):
        "Watch a ticker and update when the price changes"

        await self.watch.register(ctx.channel, ticker)


def setup(bot):
    bot.add_cog(Stocks(bot))
