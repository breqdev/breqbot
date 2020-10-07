import typing
import io
import textwrap

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import aiohttp
from resizeimage import resizeimage

import discord
from discord.ext import commands

from .base import BaseCog, UserError

bigfont = ImageFont.truetype(
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 72, encoding="unic")

smallfont = ImageFont.truetype(
    "/usr/share/fonts/truetype/ubuntu/UbuntuMono-R.ttf", 36, encoding="unic")

size = (256, 256)
mask = Image.new('L', size, 0)
draw = ImageDraw.Draw(mask)
draw.ellipse((0, 0) + size, fill=255)


class Profile(BaseCog):
    "Customize your user profile!"

    @commands.command()
    async def profile(self, ctx, user: typing.Optional[discord.User] = None):
        "Display the profile of a user!"
        if not user:
            user = ctx.author

        # Add user background
        url = (self.redis.hget(f"profile:{user.id}", "bg")
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
        desc = self.redis.hget(f"profile:{user.id}", "desc") or ""
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
    async def setprofile(self, ctx, field: str, *, value: str):
        "Set your profile!"
        fields = ("desc", "bg")

        if field not in fields:
            raise UserError(f"Invalid field {field}!")

        self.redis.hset(f"profile:{ctx.author.id}", field, value)

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Profile(bot))
