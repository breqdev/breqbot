from uuid import uuid4

import discord
from discord.ext import commands


class Item():
    def __init__(self, name=None, guild_id=None, owner_id=None,
                 desc=None, wearable=0, *, uuid=None):
        self.uuid = uuid or str(uuid4())
        self.name = name
        self.owner = owner_id if owner_id else None
        self.guild = guild_id if guild_id else None
        self.desc = desc
        self.wearable = wearable
        self.missing = False

    def __str__(self):
        return (f"{self.name}: {self.desc} "
                f"{'(wearable)' if int(self.wearable or 0) else ''} "
                f"({self.uuid})")

    @property
    def redis_key(self):
        return f"items:{self.uuid}"

    @staticmethod
    def from_dict(dict, ctx):
        item = Item(dict["name"], ctx.guild.id, ctx.author.id, dict["desc"],
                    dict["wearable"])
        return item

    @staticmethod
    async def from_redis(redis, uuid):
        exists = await redis.sismember("items:list", uuid)
        if not exists:
            item = MissingItem(uuid)
            await item.cleanup(redis)
            return item

        item = Item()
        item.uuid = uuid

        item.name = await redis.hget(item.redis_key, "name")
        item.guild = int(await redis.hget(item.redis_key, "guild") or "0")
        item.owner = int(await redis.hget(item.redis_key, "owner") or "0")
        item.desc = await redis.hget(item.redis_key, "desc")
        item.wearable = await redis.hget(item.redis_key, "wearable") or "0"
        return item

    @staticmethod
    async def from_name(redis, guild_id, name):
        name = name.strip('" ')

        uuid = await redis.get(f"items:from_name:{guild_id}:{name.lower()}")
        if not uuid:
            raise commands.CommandError("Item does not exist")

        item = await Item.from_redis(redis, uuid)
        if isinstance(item, MissingItem):
            await redis.delete(f"items:from_name:{guild_id}:{name.lower()}")
            raise commands.CommandError("Item does not exist")

        return item

    @staticmethod
    async def check_name(redis, guild_id, name):
        "Ensure the name is not in use."
        uuid = await redis.get(f"items:from_name:{guild_id}:{name.lower()}")

        if uuid is None:
            return True

        item = await Item.from_redis(redis, uuid)
        if isinstance(item, MissingItem):
            await redis.srem(f"items:list:{guild_id}", item.uuid)
            await redis.delete(f"items:from_name:{guild_id}:{name.lower()}")
            return True

        return False

    async def to_redis(self, redis):
        await redis.sadd("items:list", self.uuid)
        await redis.sadd(f"items:list:{self.guild}", self.uuid)
        await redis.sadd(f"items:list:{self.guild}:{self.owner}", self.uuid)

        await redis.hset(self.redis_key, "name", self.name)
        await redis.hset(self.redis_key, "guild", self.guild)
        await redis.hset(self.redis_key, "owner", self.owner)
        await redis.hset(self.redis_key, "desc", self.desc)
        await redis.hset(self.redis_key, "wearable", self.wearable)

        await redis.set(
            f"items:from_name:{self.guild}:{self.name.lower()}", self.uuid)

    async def rename(self, redis, newname):
        if not await self.check_name(redis, self.guild, newname):
            raise commands.Commanderror("Item name in use")

        await redis.delete(f"items:from_name:{self.guild}:{self.name.lower()}")
        self.name = newname
        await redis.hset(self.redis_key, "name", self.name)
        await redis.set(
            f"items:from_name:{self.guild}:{self.name.lower()}", self.uuid)

    async def delete(self, redis):
        await redis.srem("items:list", self.uuid)
        await redis.srem(f"items:list:{self.guild}", self.uuid)
        await redis.srem(f"items:list:{self.guild}:{self.owner}", self.uuid)

        await redis.delete(f"items:from_name:{self.guild}:{self.name.lower()}")
        await redis.delete(self.redis_key)

    def is_owner(self, user):
        return (user.id == self.owner)

    def check_owner(self, user):
        if not self.is_owner(user):
            raise commands.CommandError("You do not own this item")

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
        self.missing = True

    async def cleanup(self, redis):
        await redis.delete(f"items:{self.uuid}")


class Inventory:
    def __init__(self, user, guild, redis):
        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            user = user.id
        if isinstance(guild, discord.Guild):
            guild = guild.id
        self.user = user
        self.guild = guild
        self.redis = redis

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def ensure(self, item, qty=1):
        has = int(await self.redis.hget(
            f"inventory:{self.guild}:{self.user}", item.uuid) or "0")
        if has < qty:
            raise commands.CommandError(
                f"You need at least {qty} of {item.name}, you only have {has}")

    async def add(self, item, qty=1):
        if qty < 0:
            raise commands.CommandError("Negative numbers are not allowed.")
        await self.redis.hincrby(
            f"inventory:{self.guild}:{self.user}", item.uuid, qty)

    async def remove(self, item, qty=1):
        if qty < 0:
            raise commands.CommandError("Negative numbers are not allowed.")
        await self.ensure(item, qty)
        await self.redis.hdecrby(
            f"inventory:{self.guild}:{self.user}", item.uuid, qty)

    async def as_mapping(self):
        inventory = await self.redis.hgetall(
            f"inventory:{self.guild}:{self.user}")
        amounts = {await Item.from_redis(self.redis, item): int(amount)
                   for item, amount in inventory.items() if int(amount) > 0}

        missing = []
        for item in amounts.keys():
            if item.missing:
                await self.redis.hdel(
                    f"inventory:{self.guild}:{self.user}", item.uuid)
                missing.append(item)

        for item in missing:
            del amounts[item]

        return amounts


class Wallet:
    def __init__(self, user, guild, redis):
        if isinstance(user, discord.User) or isinstance(user, discord.Member):
            user = user.id
        if isinstance(guild, discord.Guild):
            guild = guild.id
        self.user = user
        self.guild = guild
        self.redis = redis

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def get_balance(self):
        return int(await self.redis.get(
            f"currency:balance:{self.guild}:{self.user}") or "0")

    async def ensure(self, coins):
        if await self.get_balance() < coins:
            raise commands.CommandError(f"You need at least {coins} coins!")

    async def add(self, coins):
        if coins < 0:
            raise commands.CommandError("Negative numbers are not allowed.")
        await self.redis.incrby(
            f"currency:balance:{self.guild}:{self.user}", coins)

    async def remove(self, coins):
        if coins < 0:
            raise commands.CommandError("Negative numbers are not allowed.")
        await self.redis.decrby(
            f"currency:balance:{self.guild}:{self.user}", coins)
