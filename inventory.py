import typing
import os

import discord
from discord.ext import commands

from items import Item

class Inventory(commands.Cog):
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

        balance = self.redis.get(f"currency:balance:{ctx.guild.id}:{user.id}") or 0

        await ctx.send(f"{user.name}'s Inventory:\n*Breqcoins: {balance}*\n"
                       + "\n".join(f"{item.name}: **{amount}**"
                                   for item, amount in amounts.items()))

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

        # self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -1)

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
    bot.add_cog(Inventory(bot))
