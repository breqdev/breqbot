import json
import io
import random

import requests
import discord

from ..base import UserError, run_in_executor


class XKCD():
    "View a comic from XKCD :nerd:"

    @run_in_executor
    def get_post(self, number):
        if number == "random":
            max_no = requests.get("https://xkcd.com/info.0.json").json()["num"]
            url = f"https://xkcd.com/{random.randint(1, max_no)}/info.0.json"

        elif number == "latest":
            url = "https://xkcd.com/info.0.json"
        else:
            url = f"https://xkcd.com/{number}/info.0.json"

        try:
            comic = requests.get(url).json()
        except json.decoder.JSONDecodeError:
            raise UserError(f"Comic {number} not found!")

        embed = discord.Embed()
        embed.title = f"**#{comic['num']}** | {comic['title']} | *xkcd*"
        # embed.set_image(url=comic["img"])
        embed.set_footer(text=comic["alt"])

        image = requests.get(comic["img"]).content
        image_file = discord.File(io.BytesIO(image), filename="xkcd.jpg")

        return None, [image_file], embed

    @run_in_executor
    def get_hash(self):
        return str(requests.get("https://xkcd.com/info.0.json").json()["num"])