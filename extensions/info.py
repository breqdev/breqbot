import os
import time

import discord
from discord.ext import commands

from .utils import *

startup_timestamp = time.time()

class Info(BaseCog):
    "Information and debugging tools"

    @commands.command()
    @passfail
    async def info(self, ctx):
        "Come join the bot testing server to suggest features and discuss Breqbot!"

        embed = discord.Embed(title="Hi, I'm Breqbot! Beep boop :robot:")

        embed.description = f"A bot built by the one and only Breq#8296. See {self.bot.command_prefix}help for features!"

        embed.add_field(name="Invite Breqbot to your server!",
                        value=f"[OAuth2 URL]({os.getenv('BOT_INVITE')})", inline=False)
        embed.add_field(name="Join the Breqbot discussion server!", value=os.getenv("TESTING_DISCORD"), inline=False)

        return embed

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
