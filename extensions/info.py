import os
import time

import discord
from discord.ext import commands

import git

from .utils import *

startup_timestamp = time.time()

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha

class Info(BaseCog):
    "Information and debugging tools"

    @commands.command()
    @passfail
    async def info(self, ctx):
        ":information_source: Show info about Breqbot and invite links! :incoming_envelope:"

        embed = discord.Embed(title="Hi, I'm Breqbot! Beep boop :robot:")

        embed.description = ("A bot built by the one and only Breq#8296. "
                             f"See {self.bot.command_prefix}help for "
                             "features!")

        embed.add_field(name="Invite Breqbot to your server!",
                        value=f"{os.getenv('WEBSITE')}invite",
                        inline=False)
        embed.add_field(name="Join the Breqbot discussion server!",
                        value=f"{os.getenv('TESTING_DISCORD')}", inline=False)

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
    async def stats(self, ctx):
        "Stats for nerds :robot: about the running Breqbot instance"

        embed = discord.Embed(title="`Stats for nerds`")

        fields = []

        name = self.bot.user.name + "#" + self.bot.user.discriminator
        fields.append(f"Connected as **{name}**")

        domain = os.getenv("DOMAIN")
        fields.append(f"Running on **{domain}**")

        latency = round(self.bot.latency*1000, 1)
        fields.append(f"Latency is **{latency}** ms")

        uptime = time.time() - startup_timestamp
        days_online = int(uptime / (60*60*24))
        time_str = (f"{days_online} days, "
                    + time.strftime("%T", time.gmtime(uptime)))
        fields.append(f"Uptime is **{time_str}**")

        guilds = self.redis.scard("guild:list")
        fields.append(f"Member of **{guilds}** servers")

        latest_commit = git_hash[:7]
        fields.append(f"Latest commit: `{latest_commit}`")

        embed.description = "\n".join(fields)

        return embed

    @commands.command()
    @commands.check(config_only)
    @passfail
    async def guilds(self, ctx):
        "List guilds that the bot is in"

        embed = discord.Embed(title="Breqbot is in...")

        guilds = []
        for guild_id in self.redis.smembers("guild:list"):
            guilds.append((self.redis.hget(f"guild:{guild_id}", "name"),
                          self.redis.scard(f"guild:member:{guild_id}")))

        embed.description = "\n".join(f"{name}: {size}"
                                      for name, size in guilds)
        return embed

    @commands.command()
    @passfail
    async def awsnap(self, ctx):
        "Intentionally crash the bot :skull: in order to test its error handling"
        raise ValueError("Test Exception")


def setup(bot):
    @bot.listen()
    async def on_ready():
        channel = bot.get_channel(int(os.getenv("UPDATE_CHANNEL")))
        embed = discord.Embed(title="Breqbot Connected! :blush: Hello World!")

        start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))

        embed.description = (f"Started at **{start_time}** UTC\n"
                             f"Latest commit **{git_hash[:7]}**")
        await channel.send(embed=embed)


    bot.add_cog(Info(bot))
