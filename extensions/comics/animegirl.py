import random
import io
import itertools

import requests
import bs4
import discord

from ..base import UserError, run_in_executor


class AnimeGirl():
    "View a post from 'I Want To Be A Cute Anime Girl' :transgender_flag:"

    def _get_id(self, number):
        for pageno in itertools.count(1):
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
                elif int(episode_id) == 101:
                    episode_no = "100"  # Ep. 100 is listed as "Page 100!"
                else:
                    episode_no = title.split(" ")[0]

                if number == episode_no or number == "latest":
                    return title, episode_id
                if number == "random":
                    return self._get_id(
                        str(random.randint(1, int(episode_id))))
                if episode_no == "1":
                    raise UserError(f"Episode {number} not found")

    @run_in_executor
    def get_post(self, number):
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

        caption = f"**{title}** | *I Want To Be a Cute Anime Girl!*"

        embed = discord.Embed(title=caption)
        return None, files, embed

    @run_in_executor
    def get_hash(self):
        page = requests.get("https://www.webtoons.com/en/challenge"
                            "/i-want-to-be-a-cute-anime-girl"
                            "/list?title_no=349416&page=1")
        soup = bs4.BeautifulSoup(page.content, "html.parser")
        return str(soup.find(id="_listUl").find("li").attrs["data-episode-no"])
