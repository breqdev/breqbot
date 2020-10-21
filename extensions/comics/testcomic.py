import json
import random

import requests
import discord

from ..base import UserError, run_in_executor


class TestComic():
    "this is a test"
    watchable = 1

    @run_in_executor
    def get_post(self, number):
        max_no = requests.get(
            "https://k.breq.dev/testcomic/info.json").json()["num"]

        if number == "random":
            url = ("https://k.breq.dev/testcomic/"
                   f"{random.randint(1, max_no)}.json")

        elif number == "latest":
            url = f"https://k.breq.dev/testcomic/{max_no}.json"
        else:
            url = f"https://k.breq.dev/testcomic/{number}.json"

        try:
            comic = requests.get(url).json()
        except json.decoder.JSONDecodeError:
            raise UserError(f"Comic {number} not found!")

        embed = discord.Embed()
        embed.title = f"**#{comic['title']}** | `test comic`"

        return None, [], embed

    @run_in_executor
    def get_hash(self):
        return str(requests.get(
            "https://k.breq.dev/testcomic/info.json").json()["num"])
