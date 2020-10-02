import os

from discord.ext import commands


class UserError(commands.UserInputError):
    pass


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    @staticmethod
    async def config_only(ctx):
        if not ctx.guild:
            return False
        return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
                and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))
