import os
from uuid import uuid4

from discord.ext import commands

from ..base import BaseCog


class ItemError(commands.UserInputError):
    pass


class Item():
    def __init__(self, name=None, guild_id=None, owner_id=None,
                 desc=None, wearable=0, *, uuid=None):
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
            raise ItemError("Item does not exist")

        item = Item.from_redis(redis, uuid)
        if isinstance(item, MissingItem):
            redis.delete(f"items:from_name:{guild_id}:{name.lower()}")
            raise ItemError("Item does not exist")

        return item

    @staticmethod
    def check_name(redis, guild_id, name):
        "Ensure the name is not in use."
        uuid = redis.get(f"items:from_name:{guild_id}:{name.lower()}")

        if uuid is None:
            return True

        item = Item.from_redis(redis, uuid)
        if isinstance(item, MissingItem):
            redis.srem(f"items:list:{guild_id}", item.uuid)
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

        redis.set(
            f"items:from_name:{self.guild}:{self.name.lower()}", self.uuid)

    def rename(self, redis, newname):
        if not self.check_name(redis, self.guild, newname):
            raise ItemError("Item name in use")

        redis.delete(f"items:from_name:{self.guild}:{self.name.lower()}")
        self.name = newname
        redis.hset(self.redis_key, "name", self.name)
        redis.set(
            f"items:from_name:{self.guild}:{self.name.lower()}", self.uuid)

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
            raise ItemError("You do not own this item")

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


class ItemBaseCog(BaseCog):
    @staticmethod
    async def shopkeeper_only(ctx):
        if not ctx.guild:
            return False
        if ctx.author.permissions_in(ctx.channel).administrator:
            return True
        if ctx.author.id == int(os.getenv("MAIN_SHOPKEEPER")):
            return True
        for role in ctx.author.roles:
            if role.name == "Shopkeeper":
                return True
        return False

    def ensure_item(self, ctx, user, item, qty=1):
        if qty < 0:
            raise ItemError("Negative numbers are not allowed.")
        has = int(self.redis.hget(f"inventory:{ctx.guild.id}:{user.id}",
                                  item.uuid) or "0")
        if has < qty:
            raise ItemError(f"You need at least {qty} of {item.name}, "
                            f"you only have {has}")
