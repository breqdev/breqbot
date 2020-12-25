import typing
import io

import aiohttp

import discord
from discord.ext import commands

from .. import base


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

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def card(self, ctx, *, user: typing.Optional[base.FuzzyMember]):
        "Display the profile card of a user!"
        if not user:
            user = ctx.author

        params = {
            field:
                (await self.redis.hget(
                    f"profile:{ctx.guild.id}:{user.id}", field)
                 or self.defaults[field])
            for field in self.fields
        }

        params["name"] = user.display_name
        params["avatar"] = str(user.avatar_url)
        params["format"] = "png"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                    "https://cards.breq.dev/card", params=params) as response:
                file = io.BytesIO(await response.read())

        file = discord.File(file, "card.png")

        await ctx.send(file=file)

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

            await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Card(bot))
