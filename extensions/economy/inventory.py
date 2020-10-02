import typing

import discord
from discord.ext import commands

from .itemlib import Item, MissingItem, ItemBaseCog


class InventoryError(commands.UserInputError):
    pass


class Inventory(ItemBaseCog):
    "Store items from the shop"

    @commands.command()
    @commands.guild_only()
    async def inventory(self, ctx, user: typing.Optional[discord.User]):
        "List items in your current inventory :dividers:"
        if user is None:
            user = ctx.author

        embed = discord.Embed(title=f"{user.display_name}'s Inventory")

        inventory = self.redis.hgetall(f"inventory:{ctx.guild.id}:{user.id}")
        amounts = {Item.from_redis(self.redis, item): int(amount)
                   for item, amount in inventory.items() if int(amount) > 0}

        missing = []
        for item in amounts.keys():
            if isinstance(item, MissingItem):
                self.redis.hdel(
                    f"inventory:{ctx.guild.id}:{user.id}", item.uuid)
                missing.append(item)

        for item in missing:
            del amounts[item]

        balance = (
            self.redis.get(f"currency:balance:{ctx.guild.id}:{user.id}") or 0)

        embed.description = (f"*Breqcoins: {balance}*\n"
                             + "\n".join(f"{item.name}: **{amount}**"
                                         for item, amount in amounts.items()))

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def give(self, ctx, user: discord.User, item: str,
                   amount: typing.Optional[int] = 1):
        "Give an item to another user :incoming_envelope:"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        self.ensure_item(ctx, ctx.author, item, amount)

        self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{ctx.author.id}", item.uuid, -amount)
        self.redis.hincrby(
            f"inventory:{ctx.guild.id}:{user.id}", item.uuid, amount)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def use(self, ctx, item: str):
        "Use an item [TESTING]"
        item = Item.from_name(self.redis, ctx.guild.id, item)
        self.ensure_item(ctx, ctx.author, item)

        # self.redis.hincrby(f"inventory:{ctx.guild.id}:{ctx.author.id}",
        #                    item.uuid, -1)

        await ctx.send(f"You used {item.name}. It did nothing!")


def setup(bot):
    bot.add_cog(Inventory(bot))
