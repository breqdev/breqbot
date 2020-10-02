import random
import json
import io

import requests
import bs4

import discord
from discord.ext import commands, tasks

from .utils import *


class Feed:
    @staticmethod
    async def get_post(number):
        "Return a post by its number"
        pass

    @staticmethod
    async def latest():
        "Get the number of the newest post"
        pass


class AnimeGirl(Feed):
    desc = "View a post from 'I Want To Be A Cute Anime Girl' :transgender_flag:"

    @staticmethod
    def _get_id(number):
        for pageno in range(1, 13):
            page = requests.get("https://www.webtoons.com/en/challenge"
                                "/i-want-to-be-a-cute-anime-girl"
                                f"/list?title_no=349416&page={pageno}")
            soup = bs4.BeautifulSoup(page.content, "html.parser")

            episodes = soup.find(id="_listUl")
            for episode in episodes.find_all("li", recursive=False):
                episode_id = episode.attrs["data-episode-no"]

                title = episode.find("span", class_="subj").find("span").text

                if int(episode_id) <= 50:
                    episode_no = episode_id
                else:
                    episode_no = title.split(" ")[0]

                if number == episode_no or number == "latest":
                    return title, episode_id
                if number == "random":
                    return AnimeGirl._get_id(str(random.randint(1, int(episode_id))))

        raise Fail(f"Episode {number} not found")

    @staticmethod
    @run_in_executor
    def get_post(number):
        title, episode_id = AnimeGirl._get_id(number)

        page = requests.get("https://www.webtoons.com/en/challenge"
                            "/i-want-to-be-a-cute-anime-girl/image-change/"
                            f"viewer?title_no=349416&episode_no={episode_id}")
        soup = bs4.BeautifulSoup(page.content, "html.parser")

        files = []

        images = soup.find(id="_imageList")
        for idx, image in enumerate(images.find_all("img")):
            image_file = requests.get(
                image.attrs["data-url"],
                headers={"Referer": "http://www.webtoons.com"}
            ).content

            image_file = discord.File(
                io.BytesIO(image_file), filename=f"{idx}.jpg")
            files.append(image_file)

        caption = f"**{title}** | *I Want To Be a Cute Anime Girl!*"

        embed = discord.Embed(title=title)
        return embed, files

    @staticmethod
    @run_in_executor
    def latest():
        page = requests.get("https://www.webtoons.com/en/challenge"
                            "/i-want-to-be-a-cute-anime-girl"
                            "/list?title_no=349416&page=1")
        soup = bs4.BeautifulSoup(page.content, "html.parser")
        episodes = soup.find(id="_listUl")
        episode = episodes.find("li")

        episode_id = episode.attrs["data-episode-no"]

        title = episode.find("span", class_="subj").find("span").text

        if int(episode_id) <= 50:
            episode_no = episode_id
        else:
            episode_no = title.split(" ")[0]

        return episode_no

class XKCD(Feed):
    desc = "View a comic from XKCD :nerd:"

    @staticmethod
    @run_in_executor
    def get_post(number):
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
            raise Fail(f"Comic {number} not found!")

        embed = discord.Embed()
        embed.title = f"**#{comic['num']}** | {comic['title']} | *xkcd*"
        # embed.set_image(url=comic["img"])
        embed.set_footer(text=comic["alt"])

        image = requests.get(comic["img"]).content
        image_file = discord.File(io.BytesIO(image), filename="xkcd.jpg")

        return embed, [image_file]

    @staticmethod
    @run_in_executor
    def latest():
        comic = requests.get("https://xkcd.com/info.0.json").json()
        return str(comic["num"])

comics = {
    "animegirl": AnimeGirl,
    "xkcd": XKCD,
}

feeds = comics
