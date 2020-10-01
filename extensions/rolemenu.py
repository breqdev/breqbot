import discord
from discord.ext import commands, tasks

from .utils import *


class RoleMenu(BaseCog):
    "Create and manage menus for users to choose their roles"

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    @passfail
    async def rolemenu(self, ctx):
        "Create a menu for members to choose their roles using message reactions"
        pass


def setup(bot):
    bot.add_cog(RoleMenu(bot))
