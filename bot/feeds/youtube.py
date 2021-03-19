import os

import aiohttp
import discord
from discord.ext import commands

from bot import base
from bot import watch


class Youtube(base.BaseCog, watch.Watchable):
    "See info about YouTube channels"

    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()
        self.key = os.getenv("YOUTUBE_API_KEY")

        self.watch = watch.ChannelWatch(self, crontab="*/30 * * * *")
        self.bot.watches["Youtube"] = self.watch

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

    async def get_state(self, channel_id, nsfw=None):
        async with self.session.get(
                "https://youtube.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
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

    async def get_hash(self, state):
        return state["id"]["videoId"]

    async def get_response(self, video):
        embed = discord.Embed()
        embed.title = video["snippet"]["title"]
        embed.description = video["snippet"]["description"]

        video_id = video["id"]["videoId"]
        embed.url = f"https://youtube.com/watch?v={video_id}"

        embed.set_image(url=video["snippet"]["thumbnails"]["high"]["url"])

        return base.Response("", {}, embed)

    async def human_targets(self, targets):
        return [await self.channel_name(id) for id in targets]

    async def channel_name(self, channel_id):
        async with self.session.get(
                "https://youtube.googleapis.com/youtube/v3/channels",
                params={
                    "part": "snippet",
                    "id": channel_id,
                    "maxResults": "1",
                    "key": self.key
                }) as response:
            response = await response.json()

        if response["pageInfo"]["totalResults"] < 1:
            raise commands.CommandError("No results found!")

        return response["items"][0]["snippet"]["title"]

    @commands.group(invoke_without_command=True)
    async def youtube(self, ctx, *, search: str):
        "Display info about a YouTube channel"

        channel = await self.get_channel(search, ctx.channel.is_nsfw())

        embed = discord.Embed()
        embed.title = channel["snippet"]["title"]
        embed.description = channel["snippet"]["description"]

        channel_id = channel["id"]["channelId"]
        embed.url = f"https://youtube.com/channel/{channel_id}"

        await ctx.send(embed=embed)

    @youtube.command()
    async def latest(self, ctx, *, search: str):
        "Display a YouTube channel's latest video"

        channel_id = (await self.get_channel(search))["id"]["channelId"]
        video = await self.get_state(channel_id)

        response = await self.get_response(video)
        await response.send_to(ctx)

    @youtube.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx, *, search: str):
        "Get updates for a YouTube channel"

        channel_id = (await self.get_channel(search))["id"]["channelId"]
        await self.watch.register(ctx.channel, channel_id)

        await ctx.message.add_reaction("✅")

    @youtube.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unwatch(self, ctx, *, search: str):
        "Disable updates for a YouTube channel"

        channel_id = (await self.get_channel(search))["id"]["channelId"]
        await self.watch.unregister(ctx.channel, channel_id)

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Youtube(bot))
