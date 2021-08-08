import discord
from discord.ext import commands

import aiohttp

from bot import base
from bot import watch


class Minecraft(base.BaseCog, watch.Watchable):
    "Tools for Minecraft servers"

    category = "Feeds"

    def __init__(self, bot):
        super().__init__(bot)

        self.session = aiohttp.ClientSession()
        self.watch = watch.MessageWatch(self)
        self.bot.watches["Minecraft"] = self.watch

    async def get_state(self, ip):
        async with self.session.get(
                f"https://mcstatus.breq.dev/status?server={ip}") as response:
            code = response.status
            status = await response.json()

        if code != 200:
            return ip, "Can't connect to server", (0, 0), []

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

        return ip, description, players, sample

    async def get_response(self, state):
        ip, description, players, sample = state
        embed = discord.Embed(title=ip)
        description = "**Description**\n" + description
        playerstr = f"Players: **{players[0]}**/{players[1]}"
        if sample:
            online = "\n" + "\n".join(f"• {player}" for player in sample)
        else:
            online = ""
        embed.description = description + "\n" + playerstr + online

        return base.Response(None, {}, embed)

    @commands.group(invoke_without_command=True)
    async def mc(self, ctx, ip: str):
        """:mag: :desktop: Look up information about a Minecraft server
        :video_game:"""

        response = await self.get_response(await self.get_state(ip))
        await response.send_to(ctx)

    @mc.command()
    @commands.has_guild_permissions(manage_messages=True)
    async def watch(self, ctx, ip: str):
        """Watch a Minecraft server and announce when players join or leave"""

        await self.watch.register(ctx.channel, ip)


def setup(bot):
    bot.add_cog(Minecraft(bot))
