from . import scraper, vex


class Lookup(scraper.Scraper, vex.Vex):
    pass


def setup(bot):
    bot.add_cog(Lookup(bot))
