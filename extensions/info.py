import os
import time
from datetime import timezone
import typing

import discord
from discord.ext import commands

import git

from . import base

startup_timestamp = time.time()

git_hash = os.getenv("GIT_REV") or git.Repo().head.object.hexsha


class Info(base.BaseCog):
    "Information about Breqbot"

    @commands.command()
    async def info(self, ctx):
        """:information_source: Show info about Breqbot and invite links!
        :incoming_envelope:"""

        embed = discord.Embed(title="Hi, I'm Breqbot! Beep boop :robot:")

        embed.description = (
            "A bot built by the one and only Breq#8296, "
            "full of fun commands for your server! "
            f"See `{self.bot.main_prefix}help` for features. "
            "\n\n"
            "[Invite Breqbot to your server!]"
            f"({os.getenv('WEBSITE')}invite)\n"
            "[Join the Breqbot discussion server!]"
            f"({os.getenv('WEBSITE')}guild)\n"
            "[View Breqbot's code on GitHub!]"
            f"({os.getenv('WEBSITE')}github)\n"
        )

        embed.set_image(url="https://bot.breq.dev/static/banner.png")

        await ctx.send(embed=embed)

    @commands.command()
    async def say(self, ctx, *, message: str):
        "Repeat after me!"
        await ctx.send(discord.utils.escape_mentions(message))

    @commands.command()
    async def report(self, ctx):
        "Get a link to the Discord server where you can help us patch bugs!"
        await ctx.send(f"Help us patch bugs! {os.getenv('BUG_REPORT')}")

    @commands.command()
    async def invite(self, ctx):
        "Get a link to invite the bot to your server!"
        await ctx.send("Invite Breqbot to your server! "
                       f"{os.getenv('WEBSITE')}invite")

    @commands.command()
    async def suggest(self, ctx):
        "Get a link to the Discord server where you can make suggestions!"
        await ctx.send("Suggest new features for Breqbot!"
                       f" {os.getenv('TESTING_DISCORD')}")

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

    @commands.command()
    async def website(self, ctx, user: typing.Optional[base.FuzzyMember]):
        "Link to the bot's website :computer:"
        embed = discord.Embed()

        if not ctx.guild:
            embed.title = "Breqbot Website"
            embed.url = os.getenv("WEBSITE")
        elif int(await self.redis.hget(f"guild:{ctx.guild.id}", "website")
                 or "0"):
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
                                 f"`{self.bot.main_prefix}enable website`")
        await ctx.send(embed=embed)

    @commands.command()
    async def alsotry(self, ctx):
        """Also try some other cool bots!
        Here's some small bots my friends made."""

        embed = discord.Embed(title="Also try...")

        lines = []

        for bot_id in (await self.redis.smembers("alsotry:list")):
            name = await self.redis.hget(f"alsotry:{bot_id}", "name")
            invite = await self.redis.hget(f"alsotry:{bot_id}", "invite")
            desc = await self.redis.hget(f"alsotry:{bot_id}", "desc")

            lines.append(f"[{name}]({invite}) - {desc}")

        embed.description = "\n".join(lines)

        await ctx.send(embed=embed)

    @commands.command()
    async def announcements(self, ctx):
        "Show the latest announcements!"

        embed = discord.Embed(title="Breqbot Announcements! :mega:")

        channel = self.bot.get_channel(
            int(os.getenv("ANNOUNCEMENTS_CHANNEL")))

        announcements = []

        async for message in channel.history(limit=10):
            date = message.created_at.replace(
                tzinfo=timezone.utc).astimezone(tz=None)

            content = message.content.replace("\n", "")

            content = content if len(content) < 50 else content[:47]+"..."

            announcements.append(f"**{date.strftime('%m/%d/%Y')}** "
                                 f"[{content}]({message.jump_url})")

        embed.description = "\n".join(announcements)
        await ctx.send(embed=embed)

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
    bot.add_cog(Info(bot))
