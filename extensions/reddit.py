import os
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
def get_posts(sub_name, nsfw=None, spoiler=None, flair=None):
    sub = reddit.subreddit(sub_name)

    try:
        sub.id
    except (prawcore.Redirect, prawcore.NotFound):
        raise Fail("Subreddit not found.")

    if nsfw is False and sub.over18:
        raise Fail("NSFW content is limited to NSFW channels only.")

    frontpage = sub.top("month", limit=1000)
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
        pass
        # print("Ran out of posts!")
    if images:
        image = random.choice(images)
        return image
    else:
        return "No images found!"


class Reddit(BaseCog):
    "Get memes and other posts from Reddit"
    @commands.command()
    @passfail
    async def doki(self, ctx):
        """picture of doki from ddlc!
        also try `doki fun` or ||`doki nsfw` :smirk:||"""
        async with ctx.channel.typing():
            image = await get_posts(
                "DDLC", spoiler=None, nsfw=("nsfw" in ctx.message.content),
                flair=(["Fun"] if "fun" in ctx.message.content
                       else ["Fanart", "Media"]))
        return image

    async def default(self, ctx, subreddit):
        async with ctx.channel.typing():
            image = await get_posts(subreddit, nsfw=False)
        return image

    @commands.command()
    @passfail
    async def okhet(self, ctx):
        "ok buddy hetero"
        return await self.default(ctx, "okbuddyhetero")

    @commands.command()
    @passfail
    async def wholesome(self, ctx):
        "wholesome meme"
        return await self.default(ctx, "wholesomememes")

    @commands.command()
    @passfail
    async def lgballt(self, ctx):
        "Comic from the LGBallT subreddit"
        return await self.default(ctx, "lgballt")

    @commands.command()
    @passfail
    async def meme(self, ctx):
        "Meme from r/memes"
        return await self.default(ctx, "memes")

    @commands.command()
    @passfail
    async def egg_irl(self, ctx):
        "Still cis tho... aha..."
        return await self.default(ctx, "egg_irl")

    @commands.command()
    @passfail
    async def animeme(self, ctx):
        "Meme about anime"
        return await self.default(ctx, "animemes")

    @commands.command()
    @passfail
    async def traa(self, ctx):
        "traaaaaaannnnnnnnnns"
        return await self.default(ctx, "traaaaaaannnnnnnnnns")

    @commands.command()
    @passfail
    async def reddit(self, ctx, subreddit: str):
        "post from a subreddit of your choice!"
        async with ctx.channel.typing():
            image = await get_posts(
                subreddit, nsfw=(None if ctx.channel.is_nsfw() else False))
        return image


def setup(bot):
    bot.add_cog(Reddit(bot))
