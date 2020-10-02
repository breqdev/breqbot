import json
import random

import requests
import discord

from ..base import UserError, run_in_executor
from . import feedlib


class XKCD(feedlib.Feed):
    desc = "View a comic from XKCD :nerd:"

    @run_in_executor
    def has_update(self, oldstate):
        comic = requests.get("https://xkcd.com/info.0.json").json()
        newstate = str(comic["num"])
        if newstate != oldstate:
            return newstate
        else:
            return False

    @run_in_executor
    def _get_comic(self, url):
        try:
            comic = requests.get(url).json()
        except json.decoder.JSONDecodeError:
            raise UserError(f"Comic {url} not found!")

        return comic

    async def _get_embed(self, url):
        comic = await self._get_comic(url)

        embed = discord.Embed()
        embed.title = f"**#{comic['num']}** | {comic['title']} | *xkcd*"
        embed.set_image(url=comic["img"])
        embed.set_footer(text=comic["alt"])

        return embed

    async def get_latest(self):
        return await self._get_embed("https://xkcd.com/info.0.json")

    async def get_random(self):
        comic = await self._get_comic("https://xkcd.com/info.0.json")

        random_idx = str(random.randint(1, comic["num"]))
        return await self.get_number(random_idx)

    async def get_number(self, number):
        return await self._get_embed(f"https://xkcd.com/{number}/info.0.json")
