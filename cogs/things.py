import discord
from discord.ext import commands

from .items import Item
from .breqcog import Breqcog, passfail, Fail

class Things(Breqcog):
    "Interface with real-world things"

    @commands.command()
    @passfail
    async def thing(self, ctx, thing: str, command: str):
        "Send a command to a real-world thing"
        return "Coming soon!"

def setup(bot):
    bot.add_cog(Things(bot))
