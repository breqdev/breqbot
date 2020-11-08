import json
import random

import discord

from ..base import UserError
from . import comiclib


class TestComic(comiclib.Comic):
    "this is a test"

    async def get_post(self, number):
        max_no = await self.get_url(
            "https://k.breq.dev/testcomic/info.json", type="json")["num"]

        if number == "random":
            url = ("https://k.breq.dev/testcomic/"
                   f"{random.randint(1, max_no)}.json")

        elif number == "latest":
            url = f"https://k.breq.dev/testcomic/{max_no}.json"
        else:
            url = f"https://k.breq.dev/testcomic/{number}.json"

        try:
            comic = await self.get_url(url, type="json")
        except json.decoder.JSONDecodeError:
            raise UserError(f"Comic {number} not found!")

        embed = discord.Embed()
        embed.title = f"**#{comic['title']}** | `test comic`"

        return None, [], embed

    async def get_hash(self):
        return str((await self.get_url(
            "https://k.breq.dev/testcomic/info.json", type="json"))["num"])
