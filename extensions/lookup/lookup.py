from . import minecraft, scraper, vex


class Lookup(minecraft.Minecraft, scraper.Scraper, vex.Vex):
    pass


def setup(bot):
    bot.add_cog(Lookup(bot))
