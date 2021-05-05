import os

import aiohttp
import discord
from discord.ext import commands

from bot import base
from bot import watch


class Twitter(base.BaseCog, watch.Watchable):
    "Follow a Twitter feed"

    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {os.getenv('TWITTER_API_BEARER')}"
        })

        self.watch = watch.ChannelWatch(self, crontab="*/5 * * * *")
        self.bot.watches["Twitter"] = self.watch

    async def get_user_by_username(self, username):
        if username.startswith("@"):
            username = username[1:]

        fields = ["id", "description", "name", "profile_image_url", "username"]

        async with self.session.get(
                f"https://api.twitter.com/2/users/by/username/{username}",
                params={"user.fields": ",".join(fields)}
                ) as response:
            response = await response.json()

        return response["data"]

    async def get_user_by_id(self, id):
        fields = ["id", "description", "name", "profile_image_url", "username"]

        async with self.session.get(
                f"https://api.twitter.com/2/users/{id}",
                params={"user.fields": ",".join(fields)}
                ) as response:
            response = await response.json()

        return response["data"]

    async def get_state(self, id):
        async with self.session.get(
                f"https://api.twitter.com/2/users/{id}/tweets",
                params={
                    "exclude": "retweets,replies",
                    "tweet.fields": "author_id,created_at",
                    "expansions": "attachments.media_keys",
                    "media.fields": "url"
                }) as response:
            response = await response.json()

        if response["meta"]["result_count"] < 1:
            raise commands.CommandError("No tweets found!")

        tweet = sorted(response["data"], key=lambda t: t["created_at"])[-1]
        media = response["includes"]["media"]

        media_keys = tweet.get("attachments", {}).get("media_keys", [])
        tweet["media"] = [item for item in media if item["media_key"] in media_keys]
        return tweet

    async def get_hash(self, tweet):
        return tweet["id"]

    async def get_response(self, tweet):
        embed = discord.Embed()

        user = await self.get_user_by_id(tweet["author_id"])

        embed.set_author(
            name=f"@{user['username']} ({user['name']})",
            url=f"https://twitter.com/{user['username']}",
            icon_url=user["profile_image_url"]
        )

        embed.description = tweet["text"]

        embed.url = (f"https://twitter.com/{user['username']}"
                     f"/status/{tweet['id']}")

        if tweet.get("media"):
            for media in tweet["media"]:
                if media["type"] == "photo":
                    embed.set_image(url=media["url"])
                    break

        return base.Response("", {}, embed)

    async def human_targets(self, targets):
        return [f"@{id}" for id in targets]

    @commands.group(invoke_without_command=True)
    async def twitter(self, ctx, *, username: str):
        "Display info about a Twitter account"

        user = await self.get_user_by_username(username)

        embed = discord.Embed()
        embed.set_author(
            name=f"@{user['username']} ({user['name']})",
            url=f"https://twitter.com/{user['username']}",
            icon_url=user["profile_image_url"]
        )

        embed.description = user["description"]

        await ctx.send(embed=embed)

    @twitter.command()
    async def latest(self, ctx, *, username: str):
        "Display a Twitter user's latest Tweet"

        author = await self.get_user_by_username(username)
        state = await self.get_state(author["id"])

        response = await self.get_response(state)
        await response.send_to(ctx)

    @twitter.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx, *, username: str):
        "Get updates for a Twitter account"

        author = await self.get_user_by_username(username)
        await self.watch.register(ctx.channel, author["id"])

        await ctx.message.add_reaction("✅")

    @twitter.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def unwatch(self, ctx, *, username: str):
        "Disable updates for a Twitter account"

        author = await self.get_user_by_username(username)
        await self.watch.unregister(ctx.channel, author["id"])

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Twitter(bot))
