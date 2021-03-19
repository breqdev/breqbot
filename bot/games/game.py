import os


class Game():
    def __init__(self, ctx, args, redis):
        self.ctx = ctx
        self.redis = redis
        self.args = args.split(" ") if args else []

    async def get_emoji(self, emoji_name):
        guild = self.ctx.bot.get_guild(int(os.getenv("CONFIG_GUILD")))
        for emoji in guild.emojis:
            if emoji.name == emoji_name:
                return str(emoji)
