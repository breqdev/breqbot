import discord
from discord.ext import commands

from mcstatus import MinecraftServer

from .utils import *

class Minecraft(BaseCog):
    "Tools for Minecraft servers"

    @commands.command()
    @passfail
    async def mc(self, ctx, ip: str):
        "Look up information about a Minecraft server"
        try:
            server = MinecraftServer.lookup(ip)
            status = server.status().raw
        except OSError:
            raise Fail("Could not connect to Minecraft server")

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

        description = "".join(description)
        embed.add_field(name="Description", value=description)

        playerstr = f"Players: **{status['players']['online']}**/{status['players']['max']}"

        if status["players"].get("sample"):
            online = "\n".join(f"• {player['name']}" for player in status["players"]["sample"])
        else:
            online = "None"

        embed.add_field(name=playerstr, value=online)
        return embed

def setup(bot):
    bot.add_cog(Minecraft(bot))
