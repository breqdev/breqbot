import os
from datetime import timezone
import typing

import discord
from discord.ext import commands

from .. import base


class About(base.BaseCog):
    "Information about Breqbot"

    category = "About"

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
                embed.url = ("https://breq.dev/apps/breqbot/member"
                             f"?id={user.id}&guild_id={ctx.guild.id}")
            else:
                embed.title = f"Website: **{ctx.guild.name}**"
                embed.url = ("https://breq.dev/apps/breqbot/server"
                             f"?id={ctx.guild.id}")
        else:
            embed.title = f"{ctx.guild.name}'s website is disabled."
            embed.description = (f"Admins can enable it with "
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

        if lines:
            embed.description = "\n".join(lines)
        else:
            embed.description = (
                "Breqbot doesn't feature any other bots at this time. "
                "Check back later!")

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


def setup(bot):
    bot.add_cog(About(bot))
