import os
import typing

import discord
from discord.ext import commands

from .utils import *


class Website(BaseCog):
    "Information about Breqbot's accompanying website"

    @commands.command()
    @commands.guild_only()
    @passfail
    async def website(self, ctx, user: typing.Optional[discord.User]):
        "Link to the bot's website :computer:"
        embed = discord.Embed()

        if self.redis.hget(f"guild:{ctx.guild.id}", "website"):
            if user:
                embed.title = user.display_name
                embed.description = (f"{os.getenv('WEBSITE')}user/"
                                     f"{ctx.guild.id}/{user.id}")
            else:
                embed.title = ctx.guild.name
                embed.description = (f"{os.getenv('WEBSITE')}server/"
                                     f"{ctx.guild.id}")
                embed.add_field(name=ctx.author.display_name,
                                value=f"{os.getenv('WEBSITE')}user/"
                                f"{ctx.guild.id}/{ctx.author.id}")
        else:
            embed.title = f"{ctx.guild.name}'s website is disabled."
            embed.description = (f"Shopkeepers can enable it with "
                                 f"`{self.bot.command_prefix}enwebsite 1`")
        return embed

    @commands.command()
    @commands.guild_only()
    @commands.check(shopkeeper_only)
    @passfail
    async def enwebsite(self, ctx, state: int):
        "Enable or disable the bot's website for this guild and its members :mobile_phone_off:"
        self.redis.hset(f"guild:{ctx.guild.id}", "website", state)


def setup(bot):
    bot.add_cog(Website(bot))
