import os

import aiohttp
import discord
from discord.ext import commands

from .. import base


class Youtube(base.BaseCog):
    "See info about YouTube channels"

    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()
        self.key = os.getenv("YOUTUBE_API_KEY")

    async def get_channel(self, search, nsfw=None):
        async with self.session.get(
                "https://youtube.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "maxResults": "1",
                    "q": search,
                    "safeSearch": ("none" if nsfw else "moderate"),
                    "type": "channel",
                    "key": self.key
                }) as response:
            response = await response.json()

        if response["pageInfo"]["totalResults"] < 1:
            raise commands.CommandError("No results found!")

        return response["items"][0]

    async def get_latest(self, channel, nsfw=None):
        async with self.session.get(
                "https://youtube.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": channel["id"]["channelId"],
                    "maxResults": "1",
                    "order": "date",
                    "safeSearch": ("none" if nsfw else "moderate"),
                    "type": "video",
                    "key": self.key
                }) as response:
            response = await response.json()

        if response["pageInfo"]["totalResults"] < 1:
            raise commands.CommandError("No videos found!")

        return response["items"][0]

    @commands.command()
    async def channel(self, ctx, *, search: str):
        "Display info about a YouTube channel"

        channel = await self.get_channel(search, ctx.channel.is_nsfw())

        embed = discord.Embed()
        embed.title = channel["snippet"]["title"]
        embed.description = channel["snippet"]["description"]

        channel_id = channel["id"]["channelId"]
        embed.url = f"https://youtube.com/channel/{channel_id}"

        await ctx.send(embed=embed)

    @commands.command()
    async def latestvid(self, ctx, *, search: str):
        "Display a YouTube channel's latest video"

        video = await self.get_latest(await self.get_channel(search))

        embed = discord.Embed()
        embed.title = video["snippet"]["title"]
        embed.description = video["snippet"]["description"]

        video_id = video["id"]["videoId"]
        embed.url = f"https://youtube.com/watch?v={video_id}"

        embed.set_image(url=video["snippet"]["thumbnails"]["high"]["url"])

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Youtube(bot))
