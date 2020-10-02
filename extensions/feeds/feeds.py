from discord.ext import commands

from ..base import BaseCog

from .xkcd import XKCD
from .animegirl import AnimeGirl


class BaseFeeds(BaseCog):
    pass


def make_command(name, feed):
    if feed.parameter:
        @commands.command(name=name, brief=feed.desc)
        async def _command(self, ctx, *, number: str = None):
            thisfeed = feed()
            if number is None:
                embed, files = await thisfeed.get_random()
            elif number == "latest":
                embed, files = await thisfeed.get_latest()
            elif number == "random":
                embed, files = await thisfeed.get_random()
            else:
                embed, files = await thisfeed.get_number(number)

            await ctx.send(embed=embed, files=files)
    else:
        @commands.command(name=name, brief=feed.desc)
        async def _command(self, ctx, *, number: str = None):
            thisfeed = feed()
            if number is None:
                embed, files = await thisfeed.get_random()
            elif number == "latest":
                embed, files = await thisfeed.get_latest()
            elif number == "random":
                embed, files = await thisfeed.get_random()
            else:
                embed, files = await thisfeed.get_number(number)

            await ctx.send(embed=embed, files=files)

    return _command


feeds = {
    "xkcd": XKCD,
    "animegirl": AnimeGirl,
}

new_commands = {}
for name, feed in feeds.items():
    new_commands[name] = make_command(name, feed)

Feeds = type("Feeds", (BaseFeeds,), new_commands)
Feeds.description = "View information from around the Web"


def setup(bot):
    bot.add_cog(Feeds(bot))
