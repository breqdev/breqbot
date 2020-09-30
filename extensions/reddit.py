import os
import json
import time
import random
import requests

import praw
import prawcore

import discord
from discord.ext import commands

from .utils import *

reddit = praw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"),
                     client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                     user_agent="Breqbot! https://breq.dev/")


def content_type(url):
    r = requests.head(url).headers.get("content-type")
    if r:
        return r.split(";")[0].split("/")[0]
    else:
        return "none"


@run_in_executor
def get_posts(sub_name, channel=None, redis=None, nsfw=None, spoiler=None, flair=None, text=False):
    sub = reddit.subreddit(sub_name)

    try:
        sub.id
    except (prawcore.Redirect, prawcore.NotFound):
        raise Fail("Subreddit not found.")

    if nsfw is False and sub.over18:
        raise Fail("NSFW content is limited to NSFW channels only.")

    # Clear old posts
    now = time.time()
    long_ago = now - 7200  # 2 hrs ago

    if channel:
        redis.zremrangebyscore(f"reddit:{channel}", 0, long_ago)
        redis.zremrangebyrank(f"reddit:{channel}", 0, -20)

    frontpage = sub.top("month", limit=1000)
    for submission in frontpage:
        if text:
            if not submission.is_self:
                continue
            if len(submission.selftext) > 2000:
                continue
        else:
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
            for word in flair:
                if word in submission.link_flair_text:
                    break
            else:
                continue

        if channel:
            if redis.zscore(f"reddit:{channel}", submission.id):
                continue  # Submission posted recently

        if not text:
            content = content_type(submission.url)
            if content != "image":
                continue

        redis.zadd(f"reddit:{channel}", {submission.id: now})

        if submission.is_self:
            embed = discord.Embed(title=submission.title, url=f"https://reddit.com{submission.permalink}")
            embed.description = submission.selftext
            return embed
        else:
            return f"**{submission.title}** | {submission.url}"

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

    async def default(self, ctx, params):
        async with ctx.channel.typing():
            image = await get_posts(
                params["sub"],
                channel=ctx.channel.id,
                redis=self.redis,
                nsfw=(None if ctx.channel.is_nsfw() else False),
                text=params.get("text") or False
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
        return await self.default(ctx, alias)

    return _command

new_commands = {}
for alias in aliases:
    new_commands[alias["command"]] = make_command(alias)

Reddit = type("Reddit", (BaseReddit,), new_commands)
Reddit.description = "View memes, images, and other posts from Reddit"


def setup(bot):
    bot.add_cog(Reddit(bot))
