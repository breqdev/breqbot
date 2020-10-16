import discord
from discord.ext import commands

import requests

from ..base import BaseCog, UserError, run_in_executor


class Minecraft(BaseCog):
    "Tools for Minecraft servers"
    watch_params = ("ip",)
    scan_interval = 1

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

    @commands.command()
    async def mc(self, ctx, ip: str):
        """:mag: :desktop: Look up information about a Minecraft server
        :video_game:"""
        description, players, sample = await self._get_state(ip)
        embed = discord.Embed(title=ip)
        description = "**Description**\n" + description
        playerstr = f"Players: **{players[0]}**/{players[1]}"
        if sample:
            online = "\n" + "\n".join(f"• {player}" for player in sample)
        else:
            online = ""
        embed.description = description + "\n" + playerstr + online

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Minecraft(bot))
