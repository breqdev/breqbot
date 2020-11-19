import time
import os

import git
import discord
from discord.ext import commands

from .. import base

startup_timestamp = time.time()

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha


class Debug(base.BaseCog):
    @commands.command()
    async def ping(self, ctx):
        "Pong! :ping_pong: Test system latency."
        ts = time.time()
        await ctx.send(":ping_pong:")
        full_latency = time.time() - ts
        ws_latency = round(self.bot.latency*1000, 1)
        full_latency = round(full_latency*1000, 1)
        await ctx.send(f"`WS: {ws_latency}ms  FULL: {full_latency}ms`")

    @commands.command()
    async def stats(self, ctx):
        "Stats for nerds :robot: about the running Breqbot instance"

        embed = discord.Embed(
            title="`Stats for nerds`",
            url=f"{os.getenv('WEBSITE')}status")

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

        latest_commit = git_hash[:7]
        fields.append(f"Latest commit: `{latest_commit}`")

        guilds = await self.redis.scard("guild:list")
        fields.append(f"Member of **{guilds}** servers")

        users = await self.redis.scard("user:list")
        fields.append(f"Total of **{users}** users")

        commands = await self.redis.get("commands:total_run")
        fields.append(f"**{commands}** commands run")

        embed.description = "\n".join(fields)

        await ctx.send(embed=embed)

    @commands.command()
    async def awsnap(self, ctx):
        """Intentionally crash the bot :skull:
        in order to test its error handling"""
        raise ValueError("Test Exception")

    @commands.Cog.listener()
    async def on_ready(self):
        channel = self.bot.get_channel(int(os.getenv("UPDATE_CHANNEL")))
        embed = discord.Embed(title="Breqbot Connected! :blush: Hello World!")

        start_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.gmtime(time.time()))

        embed.description = (f"Started at **{start_time}** UTC\n"
                             f"Latest commit **{git_hash[:7]}**")
        await channel.send(embed=embed)


def setup(bot):
    bot.add_cog(Debug(bot))
