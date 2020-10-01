import hashlib

import aiohttp

import discord
from discord.ext import commands, tasks

from .utils import *

class Watcher(BaseCog):
    "Keep up to date: Have Breqbot post new updates!"
    def __init__(self, bot):
        super().__init__(bot)
        self.watcher.start()

    @staticmethod
    async def get_hash(url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                content = await response.text()

        content = content.encode("utf-8")
        return hashlib.sha1(content).hexdigest()

    @commands.command()
    @passfail
    async def watch(self, ctx, url: str):
        "Watch a website for changes"
        self.redis.sadd("watcher:channels", ctx.channel.id)
        self.redis.sadd(f"watcher:list:{ctx.channel.id}", url)
        self.redis.set(f"watcher:hash:{url}", await self.get_hash(url))

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
    async def unwatch(self, ctx, url: str):
        "Stop watching a website"
        self.redis.srem(f"watcher:list:{ctx.channel.id}", url)
        self.redis.delete(f"watcher:hash:{url}")

        if self.redis.scard(f"watcher:list:{ctx.channel.id}") == 0:
            self.redis.srem("watcher:channels", ctx.channel.id)

    @tasks.loop(minutes=1)
    async def watcher(self):
        await self.bot.wait_until_ready()
        for channel_id in self.redis.smembers("watcher:channels"):
            for url in self.redis.smembers(f"watcher:list:{channel_id}"):
                oldhash = self.redis.get(f"watcher:hash:{url}")
                newhash = await self.get_hash(url)
                if oldhash != newhash:
                    await self.bot.get_channel(int(channel_id)).send(url)
                    self.redis.set(f"watcher:hash:{url}", newhash)


def setup(bot):
    bot.add_cog(Watcher(bot))
