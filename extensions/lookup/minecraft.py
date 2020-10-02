import discord
from discord.ext import commands

from mcstatus import MinecraftServer

from ..base import BaseCog, UserError


class Minecraft(BaseCog):
    "Tools for Minecraft servers"

    @commands.command()
    async def mc(self, ctx, ip: str):
        """:mag: :desktop: Look up information about a Minecraft server
        :video_game:"""
        try:
            server = MinecraftServer.lookup(ip)
            status = server.status().raw
        except OSError:
            raise UserError("Could not connect to Minecraft server")

        embed = discord.Embed(title=ip)

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

        description = "**Description**\n" + "".join(description)

        playerstr = (f"Players: **{status['players']['online']}**"
                     f"/{status['players']['max']}")

        if status["players"].get("sample"):
            online = "\n" + "\n".join(f"• {player['name']}" for player
                                      in status["players"]["sample"])
        else:
            online = ""

        embed.description = description + "\n" + playerstr + online
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Minecraft(bot))
