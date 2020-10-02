import random
import json
import io

import requests
import bs4

import discord
from discord.ext import commands

from .utils import *
from . import feed

class BaseComics(BaseCog):
    pass

def make_command(name, comic):
    @commands.command(name=name, brief=comic.desc)
    @passfail
    async def _command(self, ctx, *, number: str = "latest"):
        embed, files = await comic.get_post(number)
        await ctx.send(embed=embed, files=files)
        return NoReact

    return _command

new_commands = {}
for name, comic in feed.comics.items():
    new_commands[name] = make_command(name, comic)

Comics = type("Comics", (BaseComics,), new_commands)
Comics.description = "View some cool comics!"

def setup(bot):
    bot.add_cog(Comics(bot))
