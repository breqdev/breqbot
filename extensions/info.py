import os
import time
import typing

import discord
from discord.ext import commands

import git

from .base import BaseCog

startup_timestamp = time.time()

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha


class Info(BaseCog):
    "Information and debugging tools"

    @commands.command()
    async def info(self, ctx):
        """:information_source: Show info about Breqbot and invite links!
        :incoming_envelope:"""

        embed = discord.Embed(title="Hi, I'm Breqbot! Beep boop :robot:")

        embed.description = ("A bot built by the one and only Breq#8296. "
                             f"See {self.bot.main_prefix}help for "
                             "features!")

        embed.add_field(name="Invite Breqbot to your server!",
                        value=f"{os.getenv('WEBSITE')}invite",
                        inline=False)
        embed.add_field(name="Join the Breqbot discussion server!",
                        value=f"{os.getenv('TESTING_DISCORD')}", inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def ping(self, ctx):
        "Pong! :ping_pong: Test system latency."
        await ctx.send(":ping_pong:")
        latency = round(self.bot.latency*1000, 1)
        await ctx.send(f"`{latency}ms`")

    @commands.command()
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

        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(BaseCog.config_only)
    async def guilds(self, ctx):
        "List guilds that the bot is in"

        embed = discord.Embed(title="Breqbot is in...")

        guilds = []
        for guild_id in self.redis.smembers("guild:list"):
            guilds.append((self.redis.hget(f"guild:{guild_id}", "name"),
                          self.redis.scard(f"guild:member:{guild_id}")))

        embed.description = "\n".join(f"{name}: {size}"
                                      for name, size in guilds)
        await ctx.send(embed=embed)

    @commands.command()
    @commands.check(BaseCog.config_only)
    async def activity(self, ctx, *, activity: str):
        "Change Breqbot's status in Discord"
        game = discord.Game(activity)
        await self.bot.change_presence(status=discord.Status.online,
                                       activity=game)

    @commands.command()
    async def awsnap(self, ctx):
        """Intentionally crash the bot :skull:
        in order to test its error handling"""
        raise ValueError("Test Exception")

    @commands.command()
    @commands.guild_only()
    async def website(self, ctx, user: typing.Optional[discord.User]):
        "Link to the bot's website :computer:"
        embed = discord.Embed()

        if int(self.redis.hget(f"guild:{ctx.guild.id}", "website") or "0"):
            if user:
                embed.title = (f"Website: **{user.display_name}** "
                               f"on {ctx.guild.name}")
                embed.url = f"{os.getenv('WEBSITE')}{ctx.guild.id}/{user.id}"
            else:
                embed.title = f"Website: **{ctx.guild.name}**"
                embed.url = f"{os.getenv('WEBSITE')}{ctx.guild.id}"
        else:
            embed.title = f"{ctx.guild.name}'s website is disabled."
            embed.description = (f"Shopkeepers can enable it with "
                                 f"`{self.bot.main_prefix}enwebsite 1`")
        await ctx.send(embed=embed)


def setup(bot):
    @bot.listen()
    async def on_ready():
        channel = bot.get_channel(int(os.getenv("UPDATE_CHANNEL")))
        embed = discord.Embed(title="Breqbot Connected! :blush: Hello World!")

        start_time = time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.gmtime(time.time()))

        embed.description = (f"Started at **{start_time}** UTC\n"
                             f"Latest commit **{git_hash[:7]}**")
        await channel.send(embed=embed)

    bot.add_cog(Info(bot))
