import typing
import json

import discord
from discord.ext import commands

from bot import base
from . import itemlib


class Items(base.BaseCog):
    "Have fun with items! These can be purchased, traded, used, or worn."

    category = "Economy"

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def item(self, ctx, item: str):
        "Get information about an item :information_source:"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)

        embed = discord.Embed()
        embed.title = item.name
        embed.description = item.desc

        embed.add_field(name="Wearable",
                        value=("Yes" if int(item.wearable) else "No"))
        await ctx.send(embed=embed)

    @item.command()
    @commands.guild_only()
    async def list(self, ctx, user: typing.Optional[base.FuzzyMember] = None):
        "Get a list of items, optionally filter by creator :dividers:"
        if user:
            uuids = await self.redis.smembers(
                f"items:list:{ctx.guild.id}:{user.id}")
        else:
            uuids = await self.redis.smembers(f"items:list:{ctx.guild.id}")

        items = []
        for uuid in uuids:
            item = await itemlib.Item.from_redis(self.redis, uuid)
            if item.missing:
                if user:
                    await self.redis.srem(
                        f"items:list:{ctx.guild.id}:{user.id}", uuid)
                else:
                    await self.redis.srem(f"items:list:{ctx.guild.id}", uuid)
            else:
                items.append(item)

        embed = discord.Embed(title=f"Items on {ctx.guild.name}")

        if items:
            embed.description = "\n".join(
                f"• {item.name}: {item.desc}"
                + (" *(wearable)*" if int(item.wearable) else "")
                for item in items)
        else:
            embed.description = (
                "There are currently no items here."
                f"`{self.bot.main_prefix}item create`?")

        await ctx.send(embed=embed)

    @item.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def create(self, ctx):
        "Create an item"

        async with base.Prompt(ctx, "Item Creator") as prompt:
            name = await prompt.input("Item name?")

            if not await itemlib.Item.check_name(
                    self.redis, ctx.guild.id, name):
                raise commands.CommandError("Name in use!")

            desc = await prompt.input("Item description?")
            wearable = await prompt.input("Wearable?", bool)

        item = itemlib.Item(
            name, ctx.guild.id, ctx.author.id, desc, int(wearable))
        await item.to_redis(self.redis)

    @item.command()
    @commands.guild_only()
    async def delete(self, ctx, item: str):
        "Delete an item"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)
        item.check_owner(ctx.author)
        await item.delete(self.redis)

        await ctx.message.add_reaction("✅")

    @item.command()
    @commands.guild_only()
    async def rename(self, ctx, oldname: str, newname: str):
        "Rename an item"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, oldname)
        item.check_owner(ctx.author)
        await item.rename(self.redis, newname)

        await ctx.message.add_reaction("✅")

    @item.command()
    @commands.guild_only()
    async def edit(self, ctx, name: str):
        "Edit an existing item"

        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, name)
        item.check_owner(ctx.author)

        async with base.Prompt(ctx, "Item Editor") as prompt:
            item.desc = await prompt.input(
                "Item description?", current=item.desc)
            item.wearable = await prompt.input(
                "Wearable?", bool, current=item.wearable)

        await item.to_redis(self.redis)

    @item.command()
    @commands.guild_only()
    async def export(self, ctx, *, item: str):
        "Export an item to import it on another server"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)

        await ctx.send(f"```{json.dumps(item.dict)}```")

    @item.command(name="import")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def import_(self, ctx, *, blob: str):
        "Import an item from another server to use it here"
        try:
            dict = json.loads(blob)
            item = itemlib.Item.from_dict(dict, ctx)
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

        async with itemlib.Inventory(user, ctx.guild, self.redis) as inventory:
            mapping = await inventory.as_mapping()

        async with itemlib.Wallet(ctx.author, ctx.guild, self.redis) as wallet:
            balance = await wallet.get_balance()

        embed.description = (f"*Breqcoins: {balance}*\n"
                             + "\n".join(f"{item.name}: **{amount}**"
                                         for item, amount in mapping.items()))

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def give(self, ctx, user: discord.User, item: str,
                   amount: typing.Optional[int] = 1):
        "Give an item to another user :incoming_envelope:"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)

        async with itemlib.Inventory(ctx.author, ctx.guild, self.redis) \
                as inventory:
            await inventory.remove(item)

        async with itemlib.Inventory(user, ctx.guild, self.redis) as inventory:
            await inventory.add(item)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def use(self, ctx, *, item: str):
        "Use an item [TESTING]"
        item = await itemlib.Item.from_name(self.redis, ctx.guild.id, item)

        async with itemlib.Inventory(ctx.author, ctx.guild, self.redis) \
                as inventory:
            await inventory.ensure(item)

        await ctx.send(f"You used {item.name}. It did nothing!")


def setup(bot):
    bot.add_cog(Items(bot))
