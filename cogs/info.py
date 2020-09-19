import os
import time
import typing

import discord
from discord.ext import commands

startup_timestamp = time.time()

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def website(self, ctx, user: typing.Optional[discord.User]):
        "Link to the bot's website!"
        if user:
            await ctx.send(f"{os.getenv('WEBSITE')}user/{ctx.guild.id}/{user.id}")
        else:
            await ctx.send(f"{os.getenv('WEBSITE')}server/{ctx.guild.id}")

    @commands.command()
    async def testing(self, ctx):
        "Come join the bot testing server to suggest features and discuss Breqbot!"
        await ctx.send("Join us and discuss features for Breqbot!")
        await ctx.send(os.getenv("TESTING_DISCORD"))

    @commands.command()
    async def ping(self, ctx):
        "Pong! :ping_pong: Test system latency."
        await ctx.send(":ping_pong:")
        latency = round(self.bot.latency*1000, 1)
        await ctx.send(f"`{latency}ms`")

    @commands.command()
    async def debug(self, ctx):
        "Display debug info about the bot"

        name = self.bot.user.name + "#" + self.bot.user.discriminator
        await ctx.send(f"Connected as **{name}**")

        domain = os.getenv("DOMAIN")
        await ctx.send(f"Running on **{domain}**")

        latency = round(self.bot.latency*1000, 1)
        await ctx.send(f"Latency: **{latency}ms**")

        uptime = time.time() - startup_timestamp
        days_online = int(uptime / (60*60*24))
        time_str = f"{days_online} days, "+time.strftime("%T", time.gmtime(uptime))
        await ctx.send(f"Online for **{time_str}**")



def setup(bot):
    bot.add_cog(Info(bot))
