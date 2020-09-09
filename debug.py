import os
import time

import discord
from discord.ext import commands

startup_timestamp = time.time()

class Debug(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
    bot.add_cog(Debug(bot))
