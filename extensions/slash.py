from . import base


class SlashCog(base.BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot.slash.get_cog_commands(self)

    def cog_unload(self):
        self.bot.slash.remove_cog_commands(self)
