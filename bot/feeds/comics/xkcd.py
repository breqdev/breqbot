import json
import io
import random

import discord
from discord.ext import commands

from bot import base
from bot.feeds.comics import comiclib


class XKCD(comiclib.Comic):
    ":nerd: A webcomic of romance, sarcasm, math, and language."

    async def get_post(self, number):
        if number == "random":
            max_no = (await self.get_url(
                "https://xkcd.com/info.0.json", type="json"))["num"]
            url = f"https://xkcd.com/{random.randint(1, max_no)}/info.0.json"

        elif number == "latest":
            url = "https://xkcd.com/info.0.json"
        else:
            url = f"https://xkcd.com/{number}/info.0.json"

        try:
            comic = await self.get_url(url, type="json")
        except json.decoder.JSONDecodeError:
            raise commands.CommandError(f"Comic {number} not found!")

        embed = discord.Embed(url=f"https://xkcd.com/{comic['num']}/")
        embed.title = f"**#{comic['num']}** | {comic['title']} | *xkcd*"
        # embed.set_image(url=comic["img"])
        embed.set_footer(text=comic["alt"])

        image = await self.get_url(comic["img"], type="bin")

        return base.Response(None, {"xkcd.jpg": io.BytesIO(image)}, embed)

    async def get_hash(self):
        return str((await self.get_url(
            "https://xkcd.com/info.0.json", type="json"))["num"])
