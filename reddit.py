import os
import random
import functools
import asyncio

import praw

from discord.ext import commands

reddit = praw.Reddit(client_id=os.getenv("REDDIT_CLIENT_ID"),
                      client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                      user_agent="Breqbot! https://breq.dev/")

def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))
    return inner

@run_in_executor
def get_posts(sub_name, nsfw=None, spoiler=None, flair=None):
    sub = reddit.subreddit(sub_name)
    frontpage = sub.top(limit=1000)
    images = []
    for submission in frontpage:
        if len(images) > 25:
            break
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
        images.append(submission.url)
    else:
        print("Ran out of posts!")
    image = random.choice(images)
    return image


class Reddit(commands.Cog):
    @commands.command()
    async def doki(self, ctx):
        "picture of doki from ddlc! also try `doki fun` or ||`doki nsfw` :smirk:||"
        async with ctx.channel.typing():
            image = await get_posts("DDLC", spoiler=None,
                                    nsfw=("nsfw" in ctx.message.content),
                                    flair=(["Fun"] if "fun" in ctx.message.content
                                           else ["Fanart", "Media"]))
        await ctx.channel.send(image)

    @commands.command()
    async def okhet(self, ctx):
        "ok buddy hetero"
        async with ctx.channel.typing():
            image = await get_posts("okbuddyhetero")
        await ctx.channel.send(image)
