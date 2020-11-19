import typing
import json

import discord
from discord.ext import commands

from .. import base
from .itemlib import Item, MissingItem, EconomyCog


class Items(EconomyCog):
    "Have fun with items! These can be purchased, traded, used, or worn."

    category = "Economy"

    @commands.command()
    @commands.guild_only()
    async def item(self, ctx, item: str):
        "Get information about an item :information_source:"
        item = await Item.from_name(self.redis, ctx.guild.id, item)

        embed = discord.Embed()
        embed.title = item.name
        embed.description = item.desc

        embed.add_field(name="Wearable",
                        value=("Yes" if int(item.wearable) else "No"))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def items(self, ctx, user: typing.Optional[base.FuzzyMember] = None):
        "Get a list of items, optionally filter by creator :dividers:"
        if user:
            uuids = await self.redis.smembers(
                f"items:list:{ctx.guild.id}:{user.id}")
        else:
            uuids = await self.redis.smembers(f"items:list:{ctx.guild.id}")

        items = []
        for uuid in uuids:
            item = await Item.from_redis(self.redis, uuid)
            if isinstance(item, MissingItem):
                if user:
                    await self.redis.srem(
                        f"items:list:{ctx.guild.id}:{user.id}", uuid)
                else:
                    await self.redis.srem(f"items:list:{ctx.guild.id}", uuid)
            else:
                items.append(item)

        embed = discord.Embed(title=f"Items on {ctx.guild.name}")

        embed.description = "\n".join(
            f"• {item.name}: {item.desc}"
            + (" *(wearable)*" if int(item.wearable) else "")
            for item in items)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.check(EconomyCog.shopkeeper_only)
    async def makeitem(self, ctx, item: str, desc: str, wearable: int = 0):
        "Create an item"
        if not await Item.check_name(self.redis, ctx.guild.id, item):
            raise commands.CommandError("Name in use!")

        item = Item(item, ctx.guild.id, ctx.author.id, desc, wearable)
        await item.to_redis(self.redis)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def delitem(self, ctx, item: str):
        "Delete an item"
        item = await Item.from_name(self.redis, ctx.guild.id, item)
        await item.check_owner(ctx.author)
        await item.delete(self.redis)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def renameitem(self, ctx, oldname: str, newname: str):
        "Rename an item"
        item = await Item.from_name(self.redis, ctx.guild.id, oldname)
        await item.check_owner(ctx.author)
        await item.rename(self.redis, newname)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def modifyitem(self, ctx, item: str, field: str, value: str):
        "Modify an item"
        item = await Item.from_name(self.redis, ctx.guild.id, item)
        await item.check_owner(ctx.author)
        if field == "desc":
            item.desc = value
        elif field == "wearable":
            item.wearable = value
        else:
            raise commands.CommandError("Invalid field!")
        await item.to_redis(self.redis)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def exportitem(self, ctx, *, item: str):
        "Export an item to import it on another server"
        item = await Item.from_name(self.redis, ctx.guild.id, item)

        await ctx.send(f"```{json.dumps(item.dict)}```")

    @commands.command()
    @commands.guild_only()
    @commands.check(EconomyCog.shopkeeper_only)
    async def importitem(self, ctx, *, blob: str):
        "Import an item from another server to use it here"
        try:
            dict = json.loads(blob)
            item = Item.from_dict(dict, ctx)
        except (json.JSONDecodeError, KeyError):
            raise commands.CommandError(
                "Invalid item import! Did you use "
                f"`{self.bot.main_prefix}exportitem` ?")
        else:
            await item.to_redis(self.redis)
            await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def inventory(self, ctx, user: typing.Optional[base.FuzzyMember]):
        "List items in your current inventory :dividers:"
        if user is None:
            user = ctx.author

        embed = discord.Embed(title=f"{user.display_name}'s Inventory")

        inventory = await self.redis.hgetall(
            f"inventory:{ctx.guild.id}:{user.id}")
        amounts = {await Item.from_redis(self.redis, item): int(amount)
                   for item, amount in inventory.items() if int(amount) > 0}

        missing = []
        for item in amounts.keys():
            if isinstance(item, MissingItem):
                await self.redis.hdel(
                    f"inventory:{ctx.guild.id}:{user.id}", item.uuid)
                missing.append(item)

        for item in missing:
            del amounts[item]

        balance = (
            await self.redis.get(f"currency:balance:{ctx.guild.id}:{user.id}")
            or 0)

        embed.description = (f"*Breqcoins: {balance}*\n"
                             + "\n".join(f"{item.name}: **{amount}**"
                                         for item, amount in amounts.items()))

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def give(self, ctx, user: discord.User, item: str,
                   amount: typing.Optional[int] = 1):
        "Give an item to another user :incoming_envelope:"
        item = await Item.from_name(self.redis, ctx.guild.id, item)
        await self.ensure_item(ctx, ctx.author, item, amount)

        await self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -amount)
        await self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{user.id}", item.uuid, amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def use(self, ctx, item: str):
        "Use an item [TESTING]"
        item = await Item.from_name(self.redis, ctx.guild.id, item)
        await self.ensure_item(ctx, ctx.author, item)

        # await self.redis.hincrby(
        #     f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -1)

        await ctx.send(f"You used {item.name}. It did nothing!")


def setup(bot):
    bot.add_cog(Items(bot))
