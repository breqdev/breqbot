import os
import typing

import discord
from discord.ext import commands

from .itemlib import ItemBaseCog


class Website(ItemBaseCog):
    "Information about Breqbot's accompanying website"

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
                                 f"`{self.bot.command_prefix}enwebsite 1`")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.check(ItemBaseCog.shopkeeper_only)
    async def enwebsite(self, ctx, state: int):
        """Enable or disable the bot's website for this guild and its members
        :mobile_phone_off:"""

        self.redis.hset(f"guild:{ctx.guild.id}", "website", state)

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Website(bot))
