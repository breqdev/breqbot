import json

import discord
from discord.ext import commands, tasks

import requests

from ..base import BaseCog, UserError, run_in_executor, graceful_task


class Minecraft(BaseCog):
    "Tools for Minecraft servers"
    @commands.Cog.listener()
    async def on_ready(self):
        self.watch_task.start()

    @run_in_executor
    def _get_state(self, ip):
        status = requests.get(f"https://mcstatus.breq.dev/status?server={ip}")

        if status.status_code != 200:
            raise UserError("Could not connect to Minecraft server")

        status = status.json()

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

    async def get_hash(self, ip):
        return json.dumps(await self._get_state(ip))

    async def get_embed(self, ip):
        description, players, sample = await self._get_state(ip)
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

        await ctx.send(embed=await self.get_embed(ip))

    @commands.command()
    async def mcwatch(self, ctx, ip: str):
        """Watch a Minecraft server and announce when players join or leave"""
        self.redis.sadd("mc:watching:ips", ip)
        self.redis.sadd(f"mc:watching:ip:{ip}", ctx.channel.id)
        self.redis.sadd(f"mc:watching:channel:{ctx.channel.id}", ip)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def mcunwatch(self, ctx, ip: str):
        """Unwatch a Minecraft server"""
        self.redis.srem(f"mc:watching:ip:{ip}", ctx.channel.id)
        self.redis.srem(f"mc:watching:channel:{ctx.channel.id}", ip)
        if not self.redis.scard(f"mc:watching:ip{ip}"):
            self.redis.srem("mc:watching:ips", ip)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def mcwatching(self, ctx):
        """List watched Minecraft servers"""

        if ctx.guild:
            name = f"#{ctx.channel.name}"
        else:
            name = f"@{ctx.author.display_name}"
        embed = discord.Embed(title=f"{name} is watching...")
        embed.description = ", ".join(
            ip for ip in self.redis.smembers(
                f"mc:watching:channel:{ctx.channel.id}"))

        await ctx.send(embed=embed)

    @tasks.loop(minutes=1)
    @graceful_task
    async def watch_task(self):
        for ip in self.redis.smembers("mc:watching:ips"):
            new_hash = await self.get_hash(ip)
            old_hash = self.redis.get(f"mc:hash:{ip}")
            if old_hash != new_hash:
                self.redis.set(f"mc:hash:{ip}", new_hash)
                for channel_id in self.redis.smembers(f"mc:watching:ip:{ip}"):
                    channel = self.bot.get_channel(int(channel_id))
                    await channel.send(embed=await self.get_embed(ip))


def setup(bot):
    bot.add_cog(Minecraft(bot))
