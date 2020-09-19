from uuid import uuid4
import typing
import os

import discord
from discord.ext import commands

class Item():
    def __init__(self, name=None, desc=None, uuid=None):
        self.uuid = uuid or str(uuid4())
        self.name = name
        self.desc = desc

    def __str__(self):
        return f"{self.name}: {self.desc} ({self.uuid})"

    @property
    def redis_key(self):
        return f"items:{self.uuid}"

    @staticmethod
    def from_redis(redis, uuid):
        exists = redis.sismember("items:list", uuid)
        if not exists:
            raise ValueError("Item does not exist")

        item = Item()
        item.uuid = uuid

        item.name = redis.hget(item.redis_key, "name")
        item.desc = redis.hget(item.redis_key, "desc")
        return item

    @staticmethod
    def from_name(redis, name):
        uuid = redis.get(f"items:from_name:{name.lower()}")
        if not uuid:
            raise ValueError("Item does not exist")
        return Item.from_redis(redis, uuid)

    @staticmethod
    def check_name(redis, name):
        "Ensure the name is not in use."
        uuid = redis.get(f"items:from_name:{name.lower()}")
        return (uuid is None)

    def to_redis(self, redis):
        redis.sadd("items:list", self.uuid)

        redis.hset(self.redis_key, "name", self.name)
        redis.hset(self.redis_key, "desc", self.desc)

        redis.set(f"items:from_name:{self.name.lower()}", self.uuid)

    def rename(self, redis, newname):
        redis.delete(f"items:from_name:{self.name.lower()}")
        self.name = newname
        redis.hset(self.redis_key, "name", self.name)
        redis.set(f"items:from_name:{self.name.lower()}", self.uuid)


    def delete(self, redis):
        redis.srem("items:list", self.uuid)
        redis.delete(f"items:from_name:{self.name.lower()}")
        redis.delete(self.redis_key)

    @property
    def dict(self):
        return {"uuid": self.uuid,
                "name": self.name,
                "desc": self.desc}

class Items(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    async def config_only(ctx):
        return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
                and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))

    @commands.command()
    async def inventory(self, ctx, user: typing.Optional[discord.User]):
        "List items in your current inventory"
        if ctx.guild is None:
            return
        if user is None:
            user = ctx.author

        inventory = self.redis.hgetall(f"inventory:{ctx.guild.id}:{user.id}")

        amounts = {Item.from_redis(self.redis, item): int(amount)
                   for item, amount in inventory.items() if int(amount) > 0}

        if amounts:
            await ctx.send(f"{user.name}'s Inventory:\n"
                           + "\n".join(f"{item.name}: {amount}"
                                       for item, amount in amounts.items()))
        else:
            await ctx.send(f"{user.name}'s inventory is empty.")

    async def ensure_item(self, ctx, user, item, qty=1):
        has = int(self.redis.hget(f"inventory:{ctx.guild.id}:{user.id}", item.uuid))
        if has < qty:
            await ctx.send(f"You need at least {qty} of {item.name}, you only have {has}")
            raise ValueError("User does not have enough of item!")

    @commands.command()
    async def give(self, ctx, user: discord.User, item: str, amount: typing.Optional[int] = 1):
        "Give an item to another user"

        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.message.send("Item does not exist!")
            return

        await self.ensure_item(ctx, ctx.author, item, amount)

        self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -amount)
        self.redis.hincrby(f"inventory:{ctx.guild.id}:{user.id}", item.uuid, amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def use(self, ctx, item: str):
        "Use an item [TESTING]"

        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        await self.ensure_item(ctx, ctx.author, item)

        self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -1)

        await ctx.message.add_reaction("✅")
        await ctx.send(f"You used {item.name}. It did nothing!")

    @commands.command()
    async def item(self, ctx, item: str):
        "Get information about an item"
        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        await ctx.send(f"{item.name}: {item.desc}")

    @commands.command()
    @commands.check(config_only)
    async def list_items(self, ctx):
        await ctx.send("Items:\n"+"\n".join(str(Item.from_redis(self.redis, uuid))
                                 for uuid in self.redis.smembers("items:list")))

    @commands.command()
    @commands.check(config_only)
    async def delete_item(self, ctx, item: str):
        item = Item.from_name(self.redis, item)
        item.delete(self.redis)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(config_only)
    async def rename_item(self, ctx, oldname: str, newname: str):
        item = Item.from_name(self.redis, oldname)
        item.rename(self.redis, newname)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(config_only)
    async def modify_item(self, ctx, item: str, desc: str):
        item = Item.from_name(self.redis, item)
        item.desc = desc
        item.to_redis(self.redis)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(config_only)
    async def create_item(self, ctx, item: str, desc: str):
        if not Item.check_name(self.redis, item):
            await ctx.send("Name in use!")
            return

        item = Item(item, desc)
        item.to_redis(self.redis)
        await ctx.message.add_reaction("✅")

def setup(bot):
    bot.add_cog(Items(bot))
