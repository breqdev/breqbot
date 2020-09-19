import typing

import discord
from discord.ext import commands

from .items import Item

class Wear(commands.Cog):
    "Wear the items in your inventory"
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    async def ensure_item(self, ctx, user, item, qty=1):
        has = int(self.redis.hget(f"inventory:{ctx.guild.id}:{user.id}", item.uuid))
        if has < qty:
            await ctx.send(f"You need at least {qty} of {item.name}, you only have {has}")
            raise ValueError("User does not have enough of item!")

    @commands.command()
    async def wear(self, ctx, item: str):
        "Wear an item"
        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        if not int(item.wearable):
            await ctx.send("Item is not wearable!")
            return

        await self.ensure_item(ctx, ctx.author, item)

        wearing = self.redis.sismember(f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        if wearing:
            await ctx.send(f"You are already wearing a {item.name}!")
            return

        self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -1)
        self.redis.sadd(f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def takeoff(self, ctx, item: str):
        "Take off an item"
        try:
            item = Item.from_name(self.redis, item)
        except ValueError:
            await ctx.send("Item does not exist!")
            return

        wearing = self.redis.sismember(f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        if not wearing:
            await ctx.send(f"You are not wearing a {item.name}!")
            return

        self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, 1)
        self.redis.srem(f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def outfit(self, ctx, user: typing.Optional[discord.User]):
        if user is None:
            user = ctx.author

        embed = discord.Embed(title=f"{user.name} is wearing...")

        items = [Item.from_redis(self.redis, uuid) for uuid in self.redis.smembers(f"wear:{ctx.guild.id}:{user.id}")]

        if items:
            embed.description = "\n".join(f"• {item.name} ({item.desc})" for item in items)
        else:
            embed.description = f"{user.name} does not have any swag. `{self.bot.command_prefix}give` them some?"

        await ctx.send(embed=embed)



def setup(bot):
    bot.add_cog(Wear(bot))
