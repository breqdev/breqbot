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

    @commands.command()
    async def channel(self, ctx, *, search: str):
        "Display info about a YouTube channel"

        async with self.session.get(
                "https://youtube.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "maxResults": "1",
                    "q": search,
                    "safeSearch": ("none" if ctx.channel.is_nsfw()
                                   else "moderate"),
                    "type": "channel",
                    "key": os.getenv("YOUTUBE_API_KEY")
                }) as response:
            response = await response.json()

        if response["pageInfo"]["totalResults"] < 1:
            raise commands.CommandError("No results found!")

        resource = response["items"][0]

        embed = discord.Embed()
        embed.title = resource["snippet"]["title"]
        embed.description = resource["snippet"]["description"]

        channel_id = resource["id"]["channelId"]
        embed.url = f"https://youtube.com/channel/{channel_id}"

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Youtube(bot))
