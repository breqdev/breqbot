import hashlib

import discord
from discord.ext import commands

from mcstatus import MinecraftServer

from ..base import UserError, run_in_executor
from .. import publisher


class Minecraft(publisher.PublisherCog):
    "Tools for Minecraft servers"
    watch_params = ("ip",)
    scan_interval = 1

    @run_in_executor
    def _get_state(self, ip):
        try:
            server = MinecraftServer.lookup(ip)
            status = server.status().raw
        except OSError:
            raise UserError("Could not connect to Minecraft server")

        description = []

        if isinstance(status["description"], dict):
            for token in status["description"]["extra"]:
                text = token["text"]
                if token.get("bold") and token.get("italic"):
                    description.append(f"***{text}***")
                elif token.get("bold"):
                    description.append(f"**{text}**")
                elif token.get("italic"):
                    description.append(f"*{text}*")
                else:
                    description.append(text)
        else:
            description.append(status["description"])

        description = "".join(description)

        players = (status["players"]["online"], status["players"]["max"])

        if status["players"].get("sample"):
            sample = [player["name"] for player in status["players"]["sample"]]
        else:
            sample = []

        return description, players, sample

    @commands.command()
    async def mc(self, ctx, ip: str):
        """:mag: :desktop: Look up information about a Minecraft server
        :video_game:"""
        content, files, embed = await self.get_update(ip)
        await ctx.send(embed=embed)

    async def get_hash(self, ip):
        description, players, sample = await self._get_state(ip)
        hashstr = f"{description} {players} {sample}"
        hash = hashlib.sha1(hashstr.encode("utf-8")).hexdigest()
        return hash

    async def get_update(self, ip):
        description, players, sample = await self._get_state(ip)
        embed = discord.Embed(title=ip)
        description = "**Description**\n" + description
        playerstr = f"Players: **{players[0]}**/{players[1]}"
        if sample:
            online = "\n" + "\n".join(f"• {player}" for player in sample)
        else:
            online = ""
        embed.description = description + "\n" + playerstr + online
        return None, [], embed


def setup(bot):
    bot.add_cog(Minecraft(bot))
