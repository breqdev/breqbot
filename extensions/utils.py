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


class Item():
    def __init__(self, name=None, guild_id=None, owner_id=None, desc=None, wearable=0, *, uuid=None):
        self.uuid = uuid or str(uuid4())
        self.name = name
        self.owner = owner_id if owner_id else None
        self.guild = guild_id if guild_id else None
        self.desc = desc
        self.wearable = wearable

    def __str__(self):
        return (f"{self.name}: {self.desc} "
                f"{'(wearable)' if int(self.wearable or 0) else ''} "
                f"({self.uuid})")

    @property
    def redis_key(self):
        return f"items:{self.uuid}"

    @staticmethod
    def from_redis(redis, uuid):
        exists = redis.sismember("items:list", uuid)
        if not exists:
            item = MissingItem(uuid)
            item.cleanup(redis)
            return item

        item = Item()
        item.uuid = uuid

        item.name = redis.hget(item.redis_key, "name")
        item.guild = int(redis.hget(item.redis_key, "guild") or "0")
        item.owner = int(redis.hget(item.redis_key, "owner") or "0")
        item.desc = redis.hget(item.redis_key, "desc")
        item.wearable = redis.hget(item.redis_key, "wearable") or "0"
        return item

    @staticmethod
    def from_name(redis, guild_id, name):
        uuid = redis.get(f"items:from_name:{guild_id}:{name.lower()}")
        if not uuid:
            raise Fail("Item does not exist")

        item = Item.from_redis(redis, uuid)
        if isinstance(item, MissingItem):
            redis.delete(f"items:from_name:{guild_id}:{name.lower()}")
            raise Fail("Item does not exist")

        return item

    @staticmethod
    def check_name(redis, guild_id, name):
        "Ensure the name is not in use."
        uuid = redis.get(f"items:from_name:{guild_id}:{name.lower()}")

        if uuid is None:
            return True

        item = Item.from_redis(redis, uuid)
        if isinstance(item, MissingItem):
            redis.srem(f"items:list:{self.guild}", item.uuid)
            redis.delete(f"items:from_name:{guild_id}:{name.lower()}")
            return True

        return False


    def to_redis(self, redis):
        redis.sadd("items:list", self.uuid)
        redis.sadd(f"items:list:{self.guild}", self.uuid)
        redis.sadd(f"items:list:{self.guild}:{self.owner}", self.uuid)

        redis.hset(self.redis_key, "name", self.name)
        redis.hset(self.redis_key, "guild", self.guild)
        redis.hset(self.redis_key, "owner", self.owner)
        redis.hset(self.redis_key, "desc", self.desc)
        redis.hset(self.redis_key, "wearable", self.wearable)

        redis.set(f"items:from_name:{self.guild}:{self.name.lower()}", self.uuid)

    def rename(self, redis, newname):
        if not check_name(redis, self.guild, newname):
            raise Fail("Item name in use")

        redis.delete(f"items:from_name:{self.guild}:{self.name.lower()}")
        self.name = newname
        redis.hset(self.redis_key, "name", self.name)
        redis.set(f"items:from_name:{self.guild}:{self.name.lower()}", self.uuid)

    def delete(self, redis):
        redis.srem("items:list", self.uuid)
        redis.srem(f"items:list:{self.guild}", self.uuid)
        redis.srem(f"items:list:{self.guild}:{self.owner}", self.uuid)

        redis.delete(f"items:from_name:{self.guild}:{self.name.lower()}")
        redis.delete(self.redis_key)

    def is_owner(self, user):
        return (user.id == self.owner)

    def check_owner(self, user):
        if not self.is_owner(user):
            raise Fail("You do not own this item")

    @property
    def dict(self):
        return {"uuid": self.uuid,
                "name": self.name,
                "guild": self.guild,
                "owner": self.owner,
                "desc": self.desc,
                "wearable": self.wearable}

class MissingItem(Item):
    def __init__(self, uuid):
        self.uuid = uuid
        self.name = "MissingNo"
        self.guild = 0
        self.owner = 0
        self.desc = "Deleted Item"
        self.wearable = "0"
        self.author = "0"

    def cleanup(self, redis):
        redis.delete(f"items:{self.uuid}")

def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))
    return inner

def text_to_emoji(text):
    emoji_text = []
    for letter in text:
        if letter in string.ascii_letters:
            emoji_text.append(emoji.emojize(
                f":regional_indicator_symbol_letter_{letter.lower()}:"))
        elif letter == " ":
            emoji_text.append(emoji.emojize(f":blue_square:"))
    return " ".join(emoji_text)


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


async def config_only(ctx):
    if not ctx.guild:
        return False
    return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
            and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))


async def shopkeeper_only(ctx):
    if ctx.author.id == int(os.getenv("MAIN_SHOPKEEPER")):
        return True
    if not ctx.guild:
        return False
    for role in ctx.author.roles:
        if role.name == "Shopkeeper":
            return True
    return False


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    def ensure_item(self, ctx, user, item, qty=1):
        has = int(self.redis.hget(f"inventory:{ctx.guild.id}:{user.id}",
                                  item.uuid) or "0")
        if has < qty:
            raise Fail(f"You need at least {qty} of {item.name}, "
                       f"you only have {has}")
