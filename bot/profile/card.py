import typing
import io

import aiohttp

import discord
from discord.ext import commands

from bot import base


CARDS_API_URL = "https://cards.api.breq.dev"


class Card(base.BaseCog):
    "Customize your user profile card!"

    category = "Profile"

    fields = {
        "bio": "Set your profile card description!",
        "background": "Pick a cool background image for your card.",
        "template": ("Set the template for the card. "
                     "Current options are 'light-profile' and 'dark-profile'.")
        # "background_image": "Set the URL for your background image!"
    }

    defaults = {
        "bio": "",
        "background": "https://breq.dev/assets/images/pansexual.png",
        "template": "light-profile"
    }

    async def freeze_card(self, guild, user):
        params = {
            field:
                (await self.redis.hget(
                    f"profile:{guild.id}:{user.id}", field)
                 or self.defaults[field])
            for field in self.fields
        }

        params["name"] = user.display_name
        params["avatar"] = str(user.avatar_url)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f"{CARDS_API_URL}/card",
                    params=params) as response:
                card_id = (await response.json())["card_id"]

        await self.redis.set(f"card:{guild.id}:{user.id}", card_id)
        return card_id

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def card(self, ctx, *, user: typing.Optional[base.FuzzyMember]):
        "Display the profile card of a user!"
        if not user:
            user = ctx.author

        card_id = await self.redis.get(f"card:{ctx.guild.id}:{user.id}")

        if not card_id:
            card_id = await self.freeze_card(ctx.guild, user)

        url = f"{CARDS_API_URL}/card/{card_id}.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                file = io.BytesIO(await response.read())

        file = discord.File(file, "card.png")
        await ctx.send(file=file)

    @card.command()
    async def update(self, ctx):
        "Update your card (e.g. if you change your profile pic)"
        await self.freeze_card(ctx.guild, ctx.author)
        await ctx.message.add_reaction("✅")

    @card.command()
    async def set(self, ctx,
                  field: typing.Optional[str] = None,
                  *, value: typing.Optional[str] = None):
        "Set your profile card!"

        if field not in self.fields:
            embed = discord.Embed(title="Profile card options")
            embed.description = "\n".join(
                f"`{key}`: {value}" for key, value in self.fields.items()
            )
            await ctx.send(embed=embed)

        elif value is None:
            current = await self.redis.hget(
                f"profile:{ctx.guild.id}:{ctx.author.id}", field)

            embed = discord.Embed(title=f"Profile card: {field}")
            embed.description = (
                f"`{field}`: {self.fields[field]}\n"
                f"Current value: `{current}`"
            )
            await ctx.send(embed=embed)

        else:
            await self.redis.hset(
                f"profile:{ctx.guild.id}:{ctx.author.id}", field, value)

            await self.freeze_card(ctx.guild, ctx.author)
            await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Card(bot))
