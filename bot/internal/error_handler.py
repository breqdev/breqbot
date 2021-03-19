import uuid
import os

import discord
from discord.ext import commands

from bot import base


class ErrorHandler(base.BaseCog):

    category = "Internal"

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        await self.redis.incr("commands:total_run")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, exception):
        if isinstance(exception, base.SilentError):
            pass

        elif (isinstance(exception, commands.CheckFailure)
                or isinstance(exception, commands.DisabledCommand)):
            await ctx.message.add_reaction("⛔")

        elif isinstance(exception, commands.UserInputError):
            embed = discord.Embed()
            embed.title = "Usage:"
            if ctx.command.signature:
                embed.description = (
                    f"`{self.bot.main_prefix}{ctx.command.qualified_name}"
                    f" {ctx.command.signature}`")
            else:
                embed.description = \
                    f"`{self.bot.main_prefix}{ctx.command.name}`"
            embed.set_footer(
                text=ctx.command.brief or ctx.command.help.split("\n")[0])
            await ctx.send(embed=embed)

        elif isinstance(exception, commands.CommandNotFound):
            # await ctx.message.add_reaction("🤔")
            pass

        elif isinstance(exception, commands.CommandInvokeError):
            error_id = str(uuid.uuid4())

            embed = discord.Embed(title="Aw, snap!")
            embed.description = ("Something went wrong while running this "
                                 "command. If this continues, "
                                 f"[report]({os.getenv('BUG_REPORT')}) "
                                 f"it to Breq. (*Error ID: {error_id}*)")

            await ctx.send(embed=embed)
            await ctx.message.add_reaction("⚠️")

            print("="*20)
            print(f"Exception raised with error ID {error_id}")
            raise exception

        elif isinstance(exception, commands.CommandError):
            await ctx.message.add_reaction("🚫")
            await ctx.send(exception)


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
