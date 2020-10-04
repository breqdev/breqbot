import json

import discord
from discord.ext import commands, tasks

from ..base import BaseCog
from .. import publisher


class Watch(BaseCog):
    "Watch a comic, Minecraft server, or other feed [UNDER HEAVY DEVELOPMENT]"

    def __init__(self, bot):
        super().__init__(bot)

        self.publishers = {}

        for name, cog in bot.cogs.items():
            if isinstance(cog, publisher.PublisherCog):
                self.publishers[name] = cog
                self.make_watch_subcommand(cog)

        self.scan_number = 0
        self.scan.start()

    async def add_watch(self, channel, publisher, params):
        parameters = json.dumps(params)
        self.redis.sadd("watching:publishers",
                        f"{publisher.qualified_name}:{parameters}")
        self.redis.sadd(
            f"watching:channels:{publisher.qualified_name}:{parameters}",
            channel)
        self.redis.sadd(f"watching:publishers:{channel}",
                        f"{publisher.qualified_name}:{parameters}")

        # Preload the first hash val
        hash = await publisher.get_hash(*params)
        self.redis.set(
            f"watching:hash:{publisher.qualified_name}:{parameters}", hash)

    async def rem_watch(self, channel, publisher, parameters):
        parameters = json.dumps(parameters)
        self.redis.srem("watching:publishers",
                        f"{publisher.qualified_name}:{parameters}")
        self.redis.srem(
            f"watching:channels:{publisher.qualified_name}:{parameters}",
            channel)
        self.redis.srem(f"watching:publishers:{channel}",
                        f"{publisher.qualified_name}:{parameters}")

    def make_watch_subcommand(self, publisher):
        @self.watch.command(name=publisher.qualified_name)
        async def _watch_command(ctx, *parameters):
            if len(parameters) != len(publisher.watch_params):
                await self.send_usage(ctx, publisher)
                return

            await self.add_watch(ctx.channel.id, publisher, parameters)
            await ctx.send(f"{ctx.channel.mention} is now watching: "
                           f"{publisher.qualified_name} "
                           f"{' '.join(parameters)}")

        @self.unwatch.command(name=publisher.qualified_name)
        async def _unwatch_command(ctx, *parameters):
            await self.rem_watch(ctx.channel.id, publisher, parameters)
            await ctx.send(f"{ctx.channel.mention} has stopped watching: "
                           f"{publisher.qualified_name} "
                           f"{' '.join(parameters)}")

    def custom_bot_help(self, ctx):
        return " ".join(f"`{self.bot.command_prefix}watch {name}`"
                        for name in self.publishers) + "\n"

    async def send_usage(self, ctx, publisher):
        embed = discord.Embed(title=f"Usage: {publisher.qualified_name}")
        embed.description = (f"{self.bot.command_prefix}watch "
                             f"{publisher.qualified_name}")

        embed.description += "".join(
            f" <{param}>" for param in publisher.watch_params)

        embed.description = f"`{embed.description}`"

        await ctx.send(embed=embed)

    @commands.group()
    async def watch(self, ctx):
        "Begin watching a feed in this channel"
        if ctx.invoked_subcommand:
            return

        embed = discord.Embed(title="Available publishers")

        desc = []
        for name, pub in self.publishers.items():
            clean_params = "".join(f" <{param}>" for param in pub.watch_params)
            desc.append(f"`{self.bot.command_prefix}watch {name}"
                        f"{clean_params}`")

        embed.description = "\n".join(desc)
        await ctx.send(embed=embed)

    @commands.group()
    async def unwatch(self, ctx):
        "Stop watching a feed in this channel"
        if ctx.invoked_subcommand:
            return

        embed = discord.Embed(
            title="Invalid publisher. Valid options include:")

        desc = []
        for packed in \
                self.redis.smembers(f"watching:publishers:{ctx.channel.id}"):
            pub_name, params = packed.split(":", 1)
            params = json.loads(params)
            params = " ".join(param for param in params)
            desc.append(f"{pub_name} {params}")

        if desc:
            embed.description = "\n".join(desc)
        else:
            embed.description = ("This channel is not watching anything. ")
        await ctx.send(embed=embed)

    @commands.command()
    async def watching(self, ctx):
        "Display feeds currently being watched"
        embed = discord.Embed(title="Watching:")

        desc = []
        for packed in \
                self.redis.smembers(f"watching:publishers:{ctx.channel.id}"):
            pub_name, params = packed.split(":", 1)
            params = json.loads(params)
            params = " ".join(param for param in params)
            desc.append(f"{pub_name} {params}")

        if desc:
            embed.description = "\n".join(desc)
        else:
            embed.description = ("This channel is not watching anything. "
                                 f"Try a `{self.bot.command_prefix}watch`?")
        await ctx.send(embed=embed)

    @tasks.loop(seconds=30)
    async def scan(self):
        await self.bot.wait_until_ready()

        for packed in self.redis.smembers("watching:publishers"):
            pub_name, parameters = packed.split(":", 1)
            if self.scan_number % self.publishers[pub_name].scan_interval != 0:
                continue

            params = json.loads(parameters)
            oldhash = self.redis.get(
                f"watching:hash:{pub_name}:{parameters}")
            newhash = await self.publishers[pub_name].get_hash(*params)
            if oldhash != newhash:
                self.redis.set(
                    f"watching:hash:{pub_name}:{parameters}", newhash)

                for channel_id in self.redis.smembers(
                        f"watching:channels:{pub_name}:{parameters}"):
                    channel = self.bot.get_channel(int(channel_id))
                    content, files, embed = \
                        await (self.publishers[pub_name].get_update(*params))
                    await self.pack_send(channel, content, files, embed)

        self.scan_number += 1


def setup(bot):
    bot.add_cog(Watch(bot))
