import json

import aiocron
import discord
from discord.ext import commands

import aiohttp

from .. import base


class Minecraft(base.BaseCog):
    "Tools for Minecraft servers"

    category = "Feeds"

    @commands.Cog.listener()
    async def on_ready(self):
        self.session = aiohttp.ClientSession()

        @aiocron.crontab("*/1 * * * *")
        async def watch_task():
            for ip in await self.redis.smembers("mc:watching:ips"):
                state = await self.get_state(ip)
                new_hash = json.dumps(state)

                old_hash = await self.redis.get(f"mc:hash:{ip}")
                if old_hash != new_hash:
                    await self.redis.set(f"mc:hash:{ip}", new_hash)
                    for pair in \
                            await self.redis.smembers(f"mc:watching:ip:{ip}"):

                        channel_id, message_id = [
                            int(token) for token in pair.split(":")]

                        channel = self.bot.get_channel(channel_id)
                        try:
                            message = await channel.fetch_message(message_id)
                        except discord.errors.NotFound:
                            pass
                        else:
                            embed = self.get_embed(ip, state)
                            await message.edit(embed=embed)

    async def get_state(self, ip):
        async with self.session.get(
                f"https://mcstatus.breq.dev/status?server={ip}") as response:
            code = response.status
            status = await response.json()

        if code != 200:
            return "Can't connect to server", (0, 0), []

        description = []

        # Use a zero width space to ensure proper Markdown rendering
        zwsp = "\u200b"

        for token in status["description"]:
            text = token["text"]
            if token.get("bold") and token.get("italic"):
                description.append(f"{zwsp}***{text}***{zwsp}")
            elif token.get("bold"):
                description.append(f"{zwsp}**{text}**{zwsp}")
            elif token.get("italic"):
                description.append(f"{zwsp}*{text}*{zwsp}")
            else:
                description.append(text)

        description = "".join(description)

        players = (status["players"]["online"], status["players"]["max"])

        if status["players"].get("sample"):
            sample = [player["name"] for player in status["players"]["sample"]]
        else:
            sample = []

        return description, players, sample

    def get_embed(self, ip, state):
        description, players, sample = state
        embed = discord.Embed(title=ip)
        description = "**Description**\n" + description
        playerstr = f"Players: **{players[0]}**/{players[1]}"
        if sample:
            online = "\n" + "\n".join(f"• {player}" for player in sample)
        else:
            online = ""
        embed.description = description + "\n" + playerstr + online

        return embed

    @commands.command()
    async def mc(self, ctx, ip: str):
        """:mag: :desktop: Look up information about a Minecraft server
        :video_game:"""

        embed = self.get_embed(ip, await self.get_state(ip))
        await ctx.send(embed=embed)

    @commands.command()
    async def mcwatch(self, ctx, ip: str):
        """Watch a Minecraft server and announce when players join or leave"""

        embed = self.get_embed(ip, await self.get_state(ip))

        message = await ctx.send(embed=embed)

        await self.redis.sadd("mc:watching:ips", ip)
        await self.redis.sadd(
            f"mc:watching:ip:{ip}",
            f"{ctx.channel.id}:{message.id}")
        await self.redis.set(
            f"mc:watching:message:{ctx.channel.id}:{message.id}", ip)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        ip = await self.redis.get(
            "mc:watching:message:"
            f"{payload.channel_id}:{payload.message_id}")

        if ip is None:
            return

        await self.redis.delete(
            f"mc:watching:channel:{payload.channel_id}:{payload.message_id}")

        await self.redis.srem(
            f"mc:watching:ip:{ip}",
            f"{payload.channel_id}:{payload.message_id}")

        if not await self.redis.scard(f"mc:watching:ip:{ip}"):
            await self.redis.srem("mc:watching:ips", ip)


def setup(bot):
    bot.add_cog(Minecraft(bot))
