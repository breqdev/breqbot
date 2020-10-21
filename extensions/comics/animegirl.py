import random
import io
import itertools

import requests
import bs4
import discord

from ..base import UserError, run_in_executor


class AnimeGirl():
    """:transgender_flag: Charon's sister dressed him up as a girl, and
    he liked it. This is their story, learning about who they are, and their
    friends and family around them. """

    def _get_id(self, number):
        for pageno in itertools.count(1):
            page = requests.get("https://www.webtoons.com/en/challenge"
                                "/i-want-to-be-a-cute-anime-girl"
                                f"/list?title_no=349416&page={pageno}")
            soup = bs4.BeautifulSoup(page.content, "html.parser")

            episodes = soup.find(id="_listUl")
            for episode in episodes.find_all("li", recursive=False):
                episode_id = episode.attrs["data-episode-no"]

                if number == "random":
                    return self._get_id(
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
