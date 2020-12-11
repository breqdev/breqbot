import discord
from discord.ext import commands

from .. import base


class Watching(base.BaseCog):

    category = "Feeds"

    async def get_watching(self, channel):
        watching = {}

        for name, watch in self.bot.watches.items():
            watching[name] = await watch.human_targets(channel)

        return watching

    @commands.command()
    async def watching(self, ctx):
        "List the Feeds that this channel is subscribed to"

        if ctx.guild:
            name = f"#{ctx.channel.name}"
        else:
            name = f"@{ctx.author.display_name}"

        embed = discord.Embed(title=f"{name} is watching...")

        watching = await self.get_watching(ctx.channel)

        for name, targets in watching.items():
            if targets:
                embed.add_field(
                    name=name, value=", ".join(targets), inline=False)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Watching(bot))
