import os
import functools
import asyncio
import emoji
import string
from uuid import uuid4

import discord
from discord.ext import commands

__all__ = ["BaseCog", "Fail", "NoReact", "passfail", "config_only",
           "shopkeeper_only", "run_in_executor", "text_to_emoji", "Item",
           "MissingItem"]


class Fail(Exception):
    def __init__(self, message, debug=None):
        self.message = message
        self.debug = debug


class NoReactType:
    pass


NoReact = NoReactType()


def passfail(func):
    "Add error handling to function"

    @functools.wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        try:
            result = await func(self, ctx, *args, **kwargs)

        except Fail as e:
            await ctx.send(e.message)
            await ctx.message.add_reaction("🚫")

        except Exception as e:
            await ctx.message.add_reaction("⚠️")
            raise e  # Server failure

        else:
            # Command success
            if isinstance(result, discord.Embed):
                await ctx.send(embed=result)
            elif isinstance(result, str):
                await ctx.send(result)
            elif not isinstance(result, NoReactType):
                await ctx.message.add_reaction("✅")

    return wrapper


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis
