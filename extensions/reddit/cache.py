import os
import time
import random

import requests
import praw
import prawcore
import discord

from ..base import run_in_executor, UserError


class RedditCache:
    "Class to manage a cache of Reddit posts"
    def __init__(self, redis, config):
        self.redis = redis
        self.config = config

        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent="Breqbot! https://breq.dev/ or bot@breq.dev"
        )

    def content_type(self, url):
        "Return the MIME type of a resource located at a URL"
        try:
            r = requests.head(url).headers.get("content-type")
        except IOError:
            return "invalid"
        if r:
            return r.split(";")[0].split("/")[0]
        else:
            return "none"

    @run_in_executor
    def build_sub(self, sub_config):
        "Build the cache of posts for a specific subreddit"
        sub = self.reddit.subreddit(sub_config["sub"])

        now = time.time()

        for submission in sub.top("week", limit=100):
            if sub_config.get("text"):
                if not submission.is_self:
                    continue
                if len(submission.selftext) > 2000:
                    continue
            else:
                if submission.is_self:
                    continue

            if "spoiler" in sub_config:
                if submission.spoiler != sub_config["spoiler"]:
                    continue

            if "nsfw" in sub_config:
                if sub_config["nsfw"] is not None:
                    if submission.over_18 != sub_config["nsfw"]:
                        continue
            else:
                if submission.over_18:
                    continue

            if "flair" in sub_config:
                if submission.link_flair_text is None:
                    continue
                for word in sub_config["flair"]:
                    if word in submission.link_flair_text:
                        break
                else:
                    continue

            if not sub_config.get("text"):
                content = self.content_type(submission.url)
                if content != "image":
                    continue

            self.redis.zadd(
                f"reddit:cache:list:{sub_config['command']}",
                {submission.id: now}
            )

            self.redis.hset(f"reddit:cache:{submission.id}", mapping={
                "title": submission.title,
                "url": submission.url,
                "text": submission.selftext
            })

        # Remove old posts
        old_posts = self.redis.zrangebyscore(
            f"reddit:cache:list:{sub_config['command']}", "-inf", (now-1))

        self.redis.zremrangebyscore(
            f"reddit:cache:list:{sub_config['command']}", "-inf", (now-1))

        for post_id in old_posts:
            self.redis.delete(f"reddit:cache:{post_id}")

    async def build(self):
        "Build all caches!"
        for sub_config in self.config:
            await self.build_sub(sub_config)

    async def prune_history(self):
        "Trim the history of recently sent posts"
        channels = self.redis.keys("reddit:history:*")
        for channel in channels:
            now = time.time()
            long_ago = now - 7200  # 2 hrs ago

            self.redis.zremrangebyscore(channel, 0, long_ago)
            self.redis.zremrangebyrank(channel, 0, -20)

    async def get(self, sub_config, channel_id):
        "Return a post from the cache"

        cache_size = self.redis.zcard(
            f"reddit:cache:list:{sub_config['command']}")

        if cache_size < 1:
            raise UserError("The cache is still being built!")

        post_idx = random.randint(0, cache_size-1)

        post_id = self.redis.zrange(
            f"reddit:cache:list:{sub_config['command']}",
            post_idx, post_idx)[0]

        while self.redis.zscore(f"reddit:history:{channel_id}", post_id):
            # Submission has been posted recently, fetch a new one
            post_idx = random.randint(0, cache_size-1)
            post_id = self.redis.zrange(
                f"reddit:cache:list:{sub_config['command']}",
                post_idx, post_idx)[0]

        self.redis.zadd(f"reddit:history:{channel_id}",
                        {post_id: time.time()})

        post = self.redis.hgetall(f"reddit:cache:{post_id}")

        if sub_config.get("text"):
            ret = discord.Embed()
            ret.title = post["title"]
            ret.url = post["url"]
            ret.description = post["text"]
        else:
            image = post["url"]
            title = post["title"]
            ret = f"**{title}** | {image}"

        return ret

    async def get_custom(self, sub_name, channel_id=None, nsfw=False):
        "Return a post from a non-cached subreddit"

        sub = self.reddit.subreddit(sub_name)

        try:
            sub.id
        except (prawcore.Redirect, prawcore.NotFound, prawcore.Forbidden):
            raise UserError("Subreddit not found.")

        if nsfw is False and sub.over18:
            raise UserError("NSFW content is limited to NSFW channels only.")

        now = time.time()

        frontpage = sub.top("month", limit=1000)
        for submission in frontpage:
            if nsfw is not None:
                if submission.over_18 != nsfw:
                    continue

            if channel_id:
                if self.redis.zscore(
                        f"reddit:history:{channel_id}", submission.id):
                    continue  # Submission posted recently

            self.redis.zadd(
                f"reddit:history:{channel_id}", {submission.id: now})

            if submission.is_self:
                embed = discord.Embed(
                    title=submission.title,
                    url=f"https://reddit.com{submission.permalink}")
                embed.description = submission.selftext
                return embed
            else:
                return f"**{submission.title}** | {submission.url}"

        return "No images found!"
