import io
import random

from selenium import webdriver
import discord

from ..base import UserError, run_in_executor


options = webdriver.firefox.options.Options()
options.add_argument("--headless")
options.add_argument("--width=1000")
options.add_argument("--height=1000")


class Homestuck():
    "Idk what this is but Damon likes it so"
    watchable = 0

    @run_in_executor
    def get_post(self, number):
        if number == "random":
            number = random.randint(1, 8130)

        elif number == "latest":
            number = 8130

        url = f"https://www.homestuck.com/story/{number}"

        driver = webdriver.Firefox(options=options)
        driver.get(url)
        image = driver.get_screenshot_as_png()
        driver.quit()

        image_file = discord.File(io.BytesIO(image), filename="homestuck.png")

        return None, [image_file], None
