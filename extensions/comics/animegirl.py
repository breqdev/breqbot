import random
import io
import itertools

import bs4
import discord
from discord.ext import commands

from . import comiclib


class AnimeGirl(comiclib.Comic):
    """:transgender_flag: Charon's sister dressed him up as a girl, and
    he liked it. This is their story, learning about who they are, and their
    friends and family around them. """

    async def _get_id(self, number):
        for pageno in itertools.count(1):
            url = (
                "https://www.webtoons.com/en/challenge"
                "/i-want-to-be-a-cute-anime-girl"
                f"/list?title_no=349416&page={pageno}")

            page = await self.get_url(url)

            soup = bs4.BeautifulSoup(page, "html.parser")

            episodes = soup.find(id="_listUl")
            for episode in episodes.find_all("li", recursive=False):
                episode_id = episode.attrs["data-episode-no"]

                if number == "random":
                    return await self._get_id(
                        str(random.randint(1, int(episode_id))))

                title = episode.find("span", class_="subj").find("span").text

                if number == "latest":
                    return title, episode_id

                # The first 50 episodes are numbered according to their ID's
                if int(episode_id) <= 50:
                    episode_no = episode_id

                # After that, episode numbering diverges from ID numbering
                # but episode numbers are present in the title
                # although the format is inconsistent

                else:
                    title_tokens = title.split(" ")

                    if title_tokens[0].strip().lower() == "page":
                        title_tokens = title_tokens[1:]

                    episode_no = title_tokens[0].strip().rstrip("!")

                if number == episode_no:
                    return title, episode_id

                if episode_no == "1":
                    # We have reached the first comic without any matches
                    raise commands.CommandError(
                        f"Episode {number} not found")

    async def get_post(self, number):
        title, episode_id = await self._get_id(number)

        url = ("https://www.webtoons.com/en/challenge"
               "/i-want-to-be-a-cute-anime-girl/image-change/"
               f"viewer?title_no=349416&episode_no={episode_id}")

        page = await self.get_url(url)

        soup = bs4.BeautifulSoup(page, "html.parser")

        files = []

        images = soup.find(id="_imageList")
        for idx, image in enumerate(images.find_all("img")):
            image_url = image.attrs["data-url"]
            headers = {"Referer": "http://www.webtoons.com"}

            image_file = await self.get_url(
                image_url, headers=headers, type="bin")

            image_file = discord.File(
                io.BytesIO(image_file), filename=f"{idx}.jpg")
            files.append(image_file)

        caption = f"**{title}** | *I Want To Be a Cute Anime Girl!*"

        embed = discord.Embed(title=caption, url=url)
        return None, files, embed

    async def get_hash(self):
        url = ("https://www.webtoons.com/en/challenge"
               "/i-want-to-be-a-cute-anime-girl"
               "/list?title_no=349416&page=1")

        page = await self.get_url(url)

        soup = bs4.BeautifulSoup(page, "html.parser")
        return str(soup.find(id="_listUl").find("li").attrs["data-episode-no"])
