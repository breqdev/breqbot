import os
import json
import time
import random
import requests

import praw
import prawcore

import discord
from discord.ext import commands, tasks

from ..base import BaseCog, UserError, run_in_executor, graceful_task

reddit = praw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"),
                     client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                     user_agent="Breqbot! https://breq.dev/")


def content_type(url):
    try:
        r = requests.head(url).headers.get("content-type")
    except IOError:
        return "invalid"
    if r:
        return r.split(";")[0].split("/")[0]
    else:
        return "none"


@run_in_executor
def build_post_cache(alias, redis):
    sub = reddit.subreddit(alias["sub"])

    now = time.time()

    for submission in sub.top("week", limit=100):
        if alias.get("text"):
            if not submission.is_self:
                continue
            if len(submission.selftext) > 2000:
                continue
        else:
            if submission.is_self:
                continue

        if "spoiler" in alias:
            if submission.spoiler != alias["spoiler"]:
                continue

        if "nsfw" in alias:
            if alias["nsfw"] is not None:
                if submission.over_18 != alias["nsfw"]:
                    continue
        else:
            if submission.over_18:
                continue

        if "flair" in alias:
            if submission.link_flair_text is None:
                continue
            for word in alias["flair"]:
                if word in submission.link_flair_text:
                    break
            else:
                continue

        if not alias.get("text"):
            content = content_type(submission.url)
            if content != "image":
                continue

        redis.zadd(
            f"reddit:cache:list:{alias['command']}", {submission.id: now})
        redis.hset(f"reddit:cache:{submission.id}", mapping={
            "title": submission.title,
            "url": submission.url,
            "text": submission.selftext
        })

    # Remove old posts
    old_posts = redis.zrangebyscore(
        f"reddit:cache:list:{alias['command']}", "-inf", (now-1))

    redis.zremrangebyscore(
        f"reddit:cache:list:{alias['command']}", "-inf", (now-1))

    for post_id in old_posts:
        redis.delete(f"reddit:cache:{post_id}")


@run_in_executor
def get_posts(sub_name, channel=None, redis=None, nsfw=None, spoiler=None,
              flair=None, text=False):
    sub = reddit.subreddit(sub_name)

    try:
        sub.id
    except (prawcore.Redirect, prawcore.NotFound, prawcore.Forbidden):
        raise UserError("Subreddit not found.")

    if nsfw is False and sub.over18:
        raise UserError("NSFW content is limited to NSFW channels only.")

    now = time.time()

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
            if redis.zscore(f"reddit:history:{channel}", submission.id):
                continue  # Submission posted recently

        if not text:
            content = content_type(submission.url)
            if content != "image":
                continue

        redis.zadd(f"reddit:history:{channel}", {submission.id: now})

        if submission.is_self:
            embed = discord.Embed(
                title=submission.title,
                url=f"https://reddit.com{submission.permalink}")
            embed.description = submission.selftext
            return embed
        else:
            return f"**{submission.title}** | {submission.url}"

    return "No images found!"


class BaseReddit(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.build_cache.start()
        self.prune_history.start()

    @tasks.loop(hours=3)
    @graceful_task
    async def build_cache(self):
        for alias in reversed(self.aliases):
            await build_post_cache(alias, self.redis)

    @tasks.loop(minutes=1)
    @graceful_task
    async def prune_history(self):
        channels = self.redis.keys("reddit:history:*")
        for channel in channels:
            now = time.time()
            long_ago = now - 7200  # 2 hrs ago

            self.redis.zremrangebyscore(channel, 0, long_ago)
            self.redis.zremrangebyrank(channel, 0, -20)

    async def default(self, ctx, alias):
        cache_size = self.redis.zcard(f"reddit:cache:list:{alias['command']}")

        if cache_size < 1:
            raise UserError("The cache is still being built!")

        post_idx = random.randint(0, cache_size-1)

        post_id = self.redis.zrange(f"reddit:cache:list:{alias['command']}",
                                    post_idx, post_idx)[0]

        while self.redis.zscore(f"reddit:history:{ctx.channel.id}", post_id):
            # Submission has been posted recently, fetch a new one
            post_idx = random.randint(0, cache_size-1)
            post_id = self.redis.zrange(
                f"reddit:cache:list:{alias['command']}", post_idx, post_idx)[0]

        self.redis.zadd(f"reddit:history:{ctx.channel.id}",
                        {post_id: time.time()})

        post = self.redis.hgetall(f"reddit:cache:{post_id}")

        if alias.get("text"):
            ret = discord.Embed()
            ret.title = post["title"]
            ret.url = post["url"]
            ret.description = post["text"]
        else:
            image = post["url"]
            title = post["title"]
            ret = f"**{title}** | {image}"

        return ret

    @commands.command()
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
        await ctx.send(image)


with open("extensions/reddit/reddit.json") as f:
    aliases = json.load(f)


def conditional_decorator(dec, condition):
    def decorator(func):
        if not condition:
            return func
        return dec(func)
    return decorator


def make_command(alias):
    @commands.command(name=alias["command"], brief=alias["desc"])
    @conditional_decorator(commands.is_nsfw(),
                           (alias.get("nsfw") or alias.get("some_nsfw")))
    async def _command(self, ctx):
        ret = await self.default(ctx, alias)
        if isinstance(ret, discord.Embed):
            await ctx.send(embed=ret)
        else:
            await ctx.send(ret)

    return _command


new_attrs = {}
for alias in aliases:
    new_attrs[alias["command"]] = make_command(alias)

new_attrs["aliases"] = aliases

Reddit = type("Reddit", (BaseReddit,), new_attrs)
Reddit.description = "View memes, images, and other posts from Reddit"


def setup(bot):
    bot.add_cog(Reddit(bot))
