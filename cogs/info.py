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

        if self.redis.hget(f"guild:{ctx.guild.id}", "website"):
            if user:
                embed.title = user.name
                embed.description = f"{os.getenv('WEBSITE')}user/{ctx.guild.id}/{user.id}"
            else:
                embed.title = ctx.guild.name
                embed.description = f"{os.getenv('WEBSITE')}server/{ctx.guild.id}"
                embed.add_field(name=ctx.author.name,
                                value=f"{os.getenv('WEBSITE')}user/{ctx.guild.id}/{ctx.author.id}")
        else:
            embed.title = f"{ctx.guild.name}'s website is disabled."
            embed.description = f"Shopkeepers can enable it with `{self.bot.command_prefix}enwebsite 1`"
        return embed

    @commands.command()
    @commands.check(shopkeeper_only)
    @passfail
    async def enwebsite(self, ctx, state: int):
        "Enable or disable the bot's website for this guild and its members."
        self.redis.hset(f"guild:{ctx.guild.id}", "website", state)

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

        guilds = self.redis.scard("guild:list")
        embed.add_field(name="Servers", value=f"{guilds}")

        return embed

    @commands.command()
    @commands.check(config_only)
    @passfail
    async def guilds_list(self, ctx):
        "List guilds that the bot is in"

        embed = discord.Embed(title="Breqbot is in...")

        guilds = []
        for guild_id in self.redis.smembers("guild:list"):
            guilds.append((self.redis.hget(f"guild:{guild_id}", "name"),
                          self.redis.scard(f"guild:member:{guild_id}")))

        embed.description = "\n".join(f"{name}: {size}" for name, size in guilds)
        return embed



def setup(bot):
    bot.add_cog(Info(bot))
