import uuid
import os

import discord
from discord.ext import commands

from ..base import UserError


def setup(bot):
    @bot.event
    async def on_command_completion(ctx):
        await bot.redis.incr("commands:total_run")

    @bot.event
    async def on_command_error(ctx, exception):
        if (isinstance(exception, commands.CheckFailure)
                or isinstance(exception, commands.DisabledCommand)):
            await ctx.message.add_reaction("⛔")

        elif isinstance(exception, UserError):
            await ctx.message.add_reaction("🚫")
            await ctx.send(exception)

        elif isinstance(exception, commands.UserInputError):
            embed = discord.Embed()
            embed.title = "Usage:"
            if ctx.command.signature:
                embed.description = (f"`{bot.main_prefix}{ctx.command.name}"
                                     f" {ctx.command.signature}`")
            else:
                embed.description = f"`{bot.main_prefix}{ctx.command.name}`"
            embed.set_footer(
                text=ctx.command.brief or ctx.command.help.split("\n")[0])
            await ctx.send(embed=embed)

        elif isinstance(exception, commands.CommandNotFound):
            # await ctx.message.add_reaction("🤔")
            pass

        else:
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
