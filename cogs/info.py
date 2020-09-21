import os
import time
import typing

import discord
from discord.ext import commands

from .breqcog import *

startup_timestamp = time.time()

class Info(Breqcog):
    "Information and debugging tools"

    @commands.command()
    @passfail
    async def website(self, ctx, user: typing.Optional[discord.User]):
        "Link to the bot's website!"
        embed = discord.Embed()
        if user:
            embed.title = user.name
            embed.description = f"{os.getenv('WEBSITE')}user/{ctx.guild.id}/{user.id}"
        else:
            embed.title = ctx.guild.name
            embed.description = f"{os.getenv('WEBSITE')}server/{ctx.guild.id}"
            embed.add_field(name=ctx.author.name,
                            value=f"{os.getenv('WEBSITE')}user/{ctx.guild.id}/{ctx.author.id}")
        return embed

    @commands.command()
    @passfail
    async def testing(self, ctx):
        "Come join the bot testing server to suggest features and discuss Breqbot!"
        return f"Join us and discuss features for Breqbot! {os.getenv('TESTING_DISCORD')}"

    @commands.command()
    @passfail
    async def ping(self, ctx):
        "Pong! :ping_pong: Test system latency."
        await ctx.send(":ping_pong:")
        latency = round(self.bot.latency*1000, 1)
        return f"`{latency}ms`"

    @commands.command()
    @passfail
    async def debug(self, ctx):
        "Display debug info about the bot"

        embed = discord.Embed(title="Debug")

        name = self.bot.user.name + "#" + self.bot.user.discriminator
        embed.add_field(name="Connected as", value=name)

        domain = os.getenv("DOMAIN")
        embed.add_field(name="Running on", value=domain)

        latency = round(self.bot.latency*1000, 1)
        embed.add_field(name="Latency", value=f"{latency} ms")

        uptime = time.time() - startup_timestamp
        days_online = int(uptime / (60*60*24))
        time_str = f"{days_online} days, "+time.strftime("%T", time.gmtime(uptime))
        embed.add_field(name="Uptime", value=time_str)

        return embed



def setup(bot):
    bot.add_cog(Info(bot))
