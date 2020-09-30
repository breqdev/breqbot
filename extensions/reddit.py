import os
import json
import time
import random

import praw
import prawcore

import discord
from discord.ext import commands

from .utils import *

reddit = praw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"),
                     client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                     user_agent="Breqbot! https://breq.dev/")


@run_in_executor
def get_posts(sub_name, channel=None, redis=None, nsfw=None, spoiler=None, flair=None):
    sub = reddit.subreddit(sub_name)

    try:
        sub.id
    except (prawcore.Redirect, prawcore.NotFound):
        raise Fail("Subreddit not found.")

    if nsfw is False and sub.over18:
        raise Fail("NSFW content is limited to NSFW channels only.")

    # Clear old posts
    now = time.time()
    # long_ago = now - 3600  # 1 hr ago

    if channel:
        # redis.zremrangebyscore(f"reddit:{channel}", 0, long_ago)
        redis.zremrangebyscore(f"reddit:{channel}", 0, -50)

    frontpage = sub.top("month", limit=1000)
    for submission in frontpage:
        if submission.is_self:
            continue

        if spoiler is not None:
            if submission.spoiler != spoiler:
                continue

        if nsfw is not None:
            if submission.over_18 != nsfw:
                continue

        if flair is not None:
            if submission.link_flair_text is None:
                continue
            for text in flair:
                if text in submission.link_flair_text:
                    break
            else:
                continue

        if channel:
            if redis.zscore(f"reddit:{channel}", submission.id):
                continue  # Submission posted recently

        redis.zadd(f"reddit:{channel}", {submission.id: now})

        return submission.url

    return "No images found!"


class BaseReddit(BaseCog):
    @commands.command()
    @passfail
    async def doki(self, ctx):
        """picture of doki from ddlc!
        also try `doki fun` or ||`doki nsfw` :smirk:||"""
        async with ctx.channel.typing():
            image = await get_posts(
                "DDLC",
                channel=ctx.channel.id,
                redis=self.redis,
                spoiler=None,
                nsfw=("nsfw" in ctx.message.content),
                flair=(["Fun"] if "fun" in ctx.message.content else ["Fanart", "Media"])
            )
        return image

    async def default(self, ctx, subreddit):
        async with ctx.channel.typing():
            image = await get_posts(
                subreddit,
                channel=ctx.channel.id,
                redis=self.redis,
                nsfw=(None if ctx.channel.is_nsfw() else False)
            )
        return image

    @commands.command()
    @passfail
    async def reddit(self, ctx, subreddit: str):
        "post from a subreddit of your choice!"
        channel_is_nsfw = ctx.guild and ctx.channel.is_nsfw()
        async with ctx.channel.typing():
            image = await get_posts(
                subreddit,
                channel=ctx.channel.id,
                redis=self.redis,
                nsfw=(None if channel_is_nsfw else False)
            )
        return image


with open("extensions/reddit.json") as f:
    aliases = json.load(f)

def make_command(alias):
    @commands.command(name=alias["command"], brief=alias["desc"])
    @passfail
    async def _command(self, ctx):
        return await self.default(ctx, alias["sub"])

    return _command

new_commands = {}
for alias in aliases:
    new_commands[alias["command"]] = make_command(alias)

Reddit = type("Reddit", (BaseReddit,), new_commands)
Reddit.description = "View memes, images, and other posts from Reddit"


def setup(bot):
    bot.add_cog(Reddit(bot))
