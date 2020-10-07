import os

import redis
import discord
from discord.ext import commands

prefix = os.getenv("BOT_PREFIX") or ";"

intents = discord.Intents.default()
intents.members = True

breqbot = commands.Bot(
    (prefix, "breq ", "b! ", "b!"),
    description="Hi, I'm Breqbot! Beep boop :robot:",
    intents=intents
)
breqbot.main_prefix = prefix

breqbot.redis = redis.Redis.from_url(os.getenv("REDIS_URL"),
                                     decode_responses=True)


# - General
breqbot.load_extension("extensions.info")

# Economy
breqbot.load_extension("extensions.economy.currency")
breqbot.load_extension("extensions.economy.items")

# - Reddit
breqbot.load_extension("extensions.reddit.reddit")

# - Comics
breqbot.load_extension("extensions.comics.comics")

# - Fun
breqbot.load_extension("extensions.fun.fun")

# - Portal
breqbot.load_extension("extensions.portal")

# - Lookup
breqbot.load_extension("extensions.lookup.lookup")

# - Configuration
breqbot.load_extension("extensions.config.config")
breqbot.load_extension("extensions.config.rolemenu")

# - Utility
breqbot.load_extension("extensions.utility.help_command")
breqbot.load_extension("extensions.utility.error_handler")
breqbot.load_extension("extensions.utility.guild_watch")


breqbot.run(os.getenv("DISCORD_TOKEN"))
