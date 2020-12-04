import requests
import aiohttp
import discord
from discord.ext import commands

from .. import base


class BaseReddit(base.BaseCog, command_attrs=dict(hidden=True)):
    description = "View memes, images, and other posts from Reddit"
    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)

        self.session = aiohttp.ClientSession()

    async def default(self, ctx, config_name):
        async with self.session.get(
                f"https://redditor.breq.dev/{config_name}",
                params={"channel": f"breqbot:{ctx.channel.id}"}) as response:
            post = await response.json()

        if post.get("text"):
            embed = discord.Embed()
            embed.title = post["title"]
            embed.url = post["url"]
            embed.description = post["text"]
            await ctx.send(embed=embed)
        else:
            image = post["url"]
            title = post["title"]
            ret = f"**{title}** | {image}"
            await ctx.send(ret)


config = requests.get("https://redditor.breq.dev/list").json()


def conditional_decorator(dec, condition):
    def decorator(func):
        if not condition:
            return func
        return dec(func)
    return decorator


def make_command(config_name):
    @commands.command(name=config_name, brief=config[config_name]["desc"])
    @conditional_decorator(commands.is_nsfw(),
                           (config[config_name].get("nsfw")
                            or config[config_name].get("some_nsfw")))
    async def _command(self, ctx):
        await self.default(ctx, config_name)

    return _command


new_attrs = {}
for config_name in config:
    new_attrs[config_name] = make_command(config_name)

Reddit = type("Reddit", (BaseReddit,), new_attrs)


def setup(bot):
    bot.add_cog(Reddit(bot))
