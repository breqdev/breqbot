import discord
from discord.ext import commands, tasks

from .utils import *
from . import feed as feedlib

class Watcher(BaseCog):
    "Keep up to date: Have Breqbot post new updates!"
    def __init__(self, bot):
        super().__init__(bot)
        self.watcher.start()

    @commands.command()
    @passfail
    async def feeds(self, ctx):
        "Get available feeds to watch"
        embed = discord.Embed(title="Feeds")

        feeds = []
        for name, ifeed in feedlib.feeds.items():
            feeds.append(f"• {name}: {ifeed.desc}")

        embed.description = "\n".join(feeds)
        return embed

    @commands.command()
    @passfail
    async def watch(self, ctx, feed: str):
        "Watch a feed for changes"
        if feed not in feedlib.feeds:
            raise Fail("Feed does not exist")

        self.redis.sadd("watcher:channels", ctx.channel.id)
        self.redis.sadd(f"watcher:list:{ctx.channel.id}", feed)
        self.redis.set(f"watcher:hash:{feed}", await feedlib.feeds[feed].latest())

    @commands.command()
    @passfail
    async def watching(self, ctx):
        "List the content currently being watched"

        embed = discord.Embed(title=f"#{ctx.channel.name} is watching...")

        watching = []
        for url in self.redis.smembers(f"watcher:list:{ctx.channel.id}"):
            watching.append(url)

        if watching:
            embed.description = "\n".join(watching)
        else:
            embed.description = f"This channel is not watching any URLs. Try `{self.bot.command_prefix}watch`?"
        return embed

    @commands.command()
    @passfail
    async def unwatch(self, ctx, feed: str):
        "Stop watching a feed"
        self.redis.srem(f"watcher:list:{ctx.channel.id}", feed)
        self.redis.delete(f"watcher:hash:{feed}")

        if self.redis.scard(f"watcher:list:{ctx.channel.id}") == 0:
            self.redis.srem("watcher:channels", ctx.channel.id)

    @tasks.loop(minutes=1)
    async def watcher(self):
        await self.bot.wait_until_ready()
        for channel_id in self.redis.smembers("watcher:channels"):
            for feed in self.redis.smembers(f"watcher:list:{channel_id}"):
                oldhash = self.redis.get(f"watcher:hash:{feed}")
                newhash = await feedlib.feeds[feed].latest()
                if oldhash != newhash:
                    embed, files = await feedlib.feeds[feed].get_post(newhash)
                    await self.bot.get_channel(int(channel_id)).send(embed=embed, files=files)
                    self.redis.set(f"watcher:hash:{feed}", newhash)


def setup(bot):
    bot.add_cog(Watcher(bot))
