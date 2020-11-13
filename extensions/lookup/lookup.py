import aiohttp

from . import scraper, vex


class Lookup(scraper.Scraper, vex.Vex):
    def __init__(self, bot):
        super().__init__(bot)
        self.session = aiohttp.ClientSession()


def setup(bot):
    bot.add_cog(Lookup(bot))
