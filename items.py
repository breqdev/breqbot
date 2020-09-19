import uuid
import typing

import discord
from discord.ext import commands

class Item():
    def __init__(self, name=None, desc=None, uuid=str(uuid.uuid4())):
        self.uuid = uuid
        self.name = name
        self.desc = desc

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

    def to_redis(self, redis):
        redis.sadd("items:list", self.uuid)

        redis.hset(self.redis_key, "name", self.name)
        redis.hset(self.redis_key, "desc", self.desc)

        redis.set(f"items:from_name:{self.name.lower()}", self.uuid)

    def del_redis(self, redis):
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

def setup(bot):
    bot.add_cog(Items(bot))
