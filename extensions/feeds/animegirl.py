import random
import io

import requests
import bs4
import discord

from ..base import UserError, run_in_executor
from . import feedlib


class AnimeGirl(feedlib.Feed):
    desc = ("View a post from 'I Want To Be A Cute Anime Girl' "
            ":transgender_flag:")

    def _get_id(self, number):
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
                    return self._get_id(
                        str(random.randint(1, int(episode_id))))

        raise UserError(f"Episode {number} not found")

    @run_in_executor
    def has_update(self, oldstate):
        _, newstate = self._get_id("latest")
        if newstate != oldstate:
            return newstate
        else:
            return False

    @run_in_executor
    def get_number(self, number):
        title, episode_id = self._get_id(number)

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

        embed = discord.Embed(title=title)
        return embed, files

    async def get_latest(self):
        return await self.get_number("latest")

    async def get_random(self):
        return await self.get_number("random")
