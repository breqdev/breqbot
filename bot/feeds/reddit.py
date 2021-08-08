import requests
import aiohttp
import discord
from discord.ext import commands

from bot import base
from bot import watch


class BaseReddit(
        base.BaseCog, watch.Watchable, command_attrs=dict(hidden=True)):
    description = "View memes, images, and other posts from Reddit"
    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()

        self.watch = watch.ChannelWatch(self, crontab="00 00 * * *")
        # self.watch = watch.ChannelWatch(self, crontab="* * * * *")
        self.bot.watches["Reddit"] = self.watch

    async def check_target(self, target):
        return target in config

    async def get_state(self, config_name, channel_id=""):
        async with self.session.get(
                f"https://redditor.breq.dev/{config_name}",
                params={"channel": f"breqbot:{channel_id}"}) as response:
            return await response.json()

    async def get_response(self, post):
        if post.get("text"):
            embed = discord.Embed()
            embed.title = post["title"]
            embed.url = post["url"]
            embed.description = post["text"]
            return base.Response("", {}, embed)
        else:
            image = post["url"]
            title = post["title"]
            ret = f"**{title}** | {image}"
            return base.Response(ret, {}, None)

    async def custom_bot_help(self, ctx):
        commands = " ".join(
            f"`{self.bot.main_prefix}{config_name}`" for config_name in config
            if (
                not (
                    config[config_name].get("nsfw")
                    or config[config_name].get("some_nsfw")
                ) or ctx.channel.is_nsfw()
            )
        )

        commands += (f" | `{self.bot.main_prefix}[subreddit] watch`"
                     + f" `{self.bot.main_prefix}[subreddit] unwatch`")

        return commands + "\n"

    async def custom_cog_help(self, ctx):
        embed = discord.Embed()
        embed.title = f"Reddit | {self.description}"

        commands = "• " + " ".join(
            [f"`{self.bot.main_prefix}{config_name}`"
             for config_name in config
             if (not config[config_name].get("nsfw")
                 or await base.ctx_is_nsfw(ctx))])

        commands += f"""
• `{self.bot.main_prefix} [subreddit] watch`
• `{self.bot.main_prefix} [subreddit] unwatch`
"""

        embed.add_field(name="Commands", value=commands, inline=False)

        await ctx.send(embed=embed)


config = requests.get(
    "https://redditor.breq.dev/list", params={"nsfw": True}).json()


def conditional_decorator(dec, condition):
    def decorator(func):
        if not condition:
            return func
        return dec(func)
    return decorator


def make_command(config_name):
    @commands.group(name=config_name, brief=config[config_name]["desc"],
                    invoke_without_command=True)
    @conditional_decorator(base.is_nsfw(),
                           (config[config_name].get("nsfw")
                            or config[config_name].get("some_nsfw")))
    async def _command(self, ctx):
        post = await self.get_state(config_name, ctx.channel.id)
        response = await self.get_response(post)
        await response.send_to(ctx)

    @_command.command(name="watch", brief=f"Get daily {config_name} posts!")
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx):
        await self.watch.register(ctx.channel, config_name)
        await ctx.message.add_reaction("✅")

    @_command.command(name="unwatch",
                      brief=f"Disable daily {config_name} posts")
    @commands.has_guild_permissions(manage_messages=True)
    async def unwatch(self, ctx):
        await self.watch.unregister(ctx.channel, config_name)
        await ctx.message.add_reaction("✅")

    return {
        config_name: _command,
        f"{config_name}_watch": watch,
        f"{config_name}_unwatch": unwatch
    }


new_commands = {}
for config_name in config:
    new_commands = {**new_commands, **make_command(config_name)}

Reddit = type("Reddit", (BaseReddit,), new_commands)


def setup(bot):
    bot.add_cog(Reddit(bot))
