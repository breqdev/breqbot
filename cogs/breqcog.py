import os
import functools

import discord
from discord.ext import commands

from .items import Item

__all__ = ["Breqcog", "Fail", "NoReact", "passfail", "config_only", "shopkeeper_only"]

class Fail(Exception):
    def __init__(self, message, debug=None):
        self.message = message
        self.debug = debug

class NoReact:
    pass

def passfail(func):
    "Add error handling to function"

    @functools.wraps(func)
    async def wrapper(self, ctx, *args, **kwargs):
        try:
            result = await func(self, ctx, *args, **kwargs)

        except Fail as e:
            message = await ctx.send(e.message)
            # await message.delete(delay=10)
            await ctx.message.add_reaction("🚫")

        except Exception as e:
            await ctx.message.add_reaction("⚠️")
            raise e # Server failure

        else:
            # Command success
            if isinstance(result, discord.Embed):
                await ctx.send(embed=result)
            elif isinstance(result, str):
                await ctx.send(result)
            elif not isinstance(result, NoReact):
                await ctx.message.add_reaction("✅")

    return wrapper

async def config_only(ctx):
    return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
            and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))

async def shopkeeper_only(ctx):
    if ctx.author.id == int(os.getenv("MAIN_SHOPKEEPER")):
        return True
    for role in ctx.author.roles:
        if role.name == "Shopkeeper":
            return True
    return False

class Breqcog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    def get_item(self, name):
        try:
            item = Item.from_name(self.redis, name)
        except ValueError:
            raise Fail("Item does not exist!")
        else:
            return item

    def ensure_item(self, ctx, user, item, qty=1):
        has = int(self.redis.hget(f"inventory:{ctx.guild.id}:{user.id}", item.uuid))
        if has < qty:
            raise Fail(f"You need at least {qty} of {item.name}, you only have {has}")