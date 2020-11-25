import typing
import io
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import aiohttp
from resizeimage import resizeimage

import discord
from discord.ext import commands

from .. import base

bigfont = ImageFont.truetype(
    "fonts/UbuntuMono-R.ttf", 72, encoding="unic")

smallfont = ImageFont.truetype(
    "fonts/UbuntuMono-R.ttf", 36, encoding="unic")

size = (256, 256)
mask = Image.new('L', size, 0)
draw = ImageDraw.Draw(mask)
draw.ellipse((0, 0) + size, fill=255)


class Card(base.BaseCog):
    "Customize your user profile card!"

    category = "Profile"

    fields = {
        "desc": "Set your profile card description!",
        "bg": "Set the URL for your background image!"
    }

    @commands.command()
    @commands.guild_only()
    async def card(self, ctx, user: typing.Optional[base.FuzzyMember]):
        "Display the profile card of a user!"
        if not user:
            user = ctx.author

        # Add user background
        url = (await self.redis.hget(f"profile:{ctx.guild.id}:{user.id}", "bg")
               or "https://breq.dev/assets/images/logo/white_wireframe.jpg")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                imagebytes = io.BytesIO(await response.read())
                image = Image.open(imagebytes).convert("RGB")

        image = resizeimage.resize_cover(image, (720, 376))

        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(0.5)

        draw = ImageDraw.Draw(image)

        # Add user avatar
        avatar = io.BytesIO(
            await user.avatar_url_as(format="png", size=256).read())

        avatar = Image.open(avatar)

        avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))

        image.paste(avatar, (32, 32), mask=mask)

        # Add display name
        wrap_name = "\n".join(textwrap.wrap(user.display_name, 9))
        # text_height = (wrap_name.count("\n")+1) * 80
        draw.multiline_text((320, 32), wrap_name,
                            spacing=8, font=bigfont, fill=(255, 255, 255))

        # Add user desc
        desc = await self.redis.hget(
            f"profile:{ctx.guild.id}:{user.id}", "desc") or ""
        # wrap_desc = "\n".join(textwrap.wrap(desc, 20))
        wrap_desc = desc[:30]
        width, height = draw.textsize(wrap_desc, font=smallfont)
        draw.multiline_text((360 - width/2, 320), wrap_desc,
                            font=smallfont, fill=(255, 255, 255))

        file = io.BytesIO()
        image.save(file, "png")
        file.seek(0)
        file = discord.File(file, "profile.png")

        await ctx.send(file=file)

    @commands.command()
    async def setcard(self, ctx,
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