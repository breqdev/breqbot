import typing

import discord
from discord.ext import commands

from .. import base
from ..economy.itemlib import Item, EconomyCog, MissingItem


class Outfit(EconomyCog):
    @commands.command()
    @commands.guild_only()
    async def wear(self, ctx, item: str):
        "Wear an item :lab_coat:"
        item = await Item.from_name(self.redis, ctx.guild.id, item)

        if not int(item.wearable):
            raise commands.CommandError("Item is not wearable!")
        await self.ensure_item(ctx, ctx.author, item)

        wearing = await self.redis.sismember(
            f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        if wearing:
            raise commands.CommandError(
                f"You are already wearing a {item.name}!")

        await self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -1)
        await self.redis.sadd(
            f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def takeoff(self, ctx, item: str):
        "Take off an item :x:"
        item = await Item.from_name(self.redis, ctx.guild.id, item)

        wearing = await self.redis.sismember(
            f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        if not wearing:
            raise commands.CommandError(
                f"You are not wearing a {item.name}!")

        await self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, 1)
        await self.redis.srem(
            f"wear:{ctx.guild.id}:{ctx.author.id}", item.uuid)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def outfit(self, ctx, user: typing.Optional[base.FuzzyMember]):
        "List the items that a user is wearing :lab_coat:"
        if user is None:
            user = ctx.author

        embed = discord.Embed(title=f"{user.display_name} is wearing...")

        items = [await Item.from_redis(self.redis, uuid)
                 for uuid in (await self.redis.smembers(
                     f"wear:{ctx.guild.id}:{user.id}"))]

        missing = []
        for item in items:
            if isinstance(item, MissingItem):
                missing.append(item)
                await self.redis.srem(
                    f"wear:{ctx.guild.id}:{user.id}", item.uuid)

        items = [item for item in items if item not in missing]

        if items:
            embed.description = "\n".join(f"• {item.name} ({item.desc})"
                                          for item in items)
        else:
            embed.description = (f"{user.display_name} does not have any swag."
                                 f"`{self.bot.main_prefix}give` them some?")

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Outfit(bot))
