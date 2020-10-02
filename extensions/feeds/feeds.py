from discord.ext import commands

from ..base import BaseCog

from .xkcd import XKCD


class BaseFeeds(BaseCog):
    pass


def make_command(name, feed):
    @commands.command(name=name, brief=feed.desc)
    async def _command(self, ctx, *, number: str = None):
        if number is None:
            embed = await feed.get_random()
        elif number == "latest":
            embed = await feed.get_latest()
        elif number == "random":
            embed = await feed.get_random()
        else:
            embed = await feed.get_number(number)

        await ctx.send(embed=embed)

    return _command


feeds = {
    "xkcd": XKCD(),
}

new_commands = {}
for name, feed in feeds.items():
    new_commands[name] = make_command(name, feed)

Feeds = type("Feeds", (BaseFeeds,), new_commands)
Feeds.description = "View information from around the Web"


def setup(bot):
    bot.add_cog(Feeds(bot))
