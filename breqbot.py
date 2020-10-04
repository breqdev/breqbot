import os

import redis
import discord
from discord.ext import commands

prefix = os.getenv("BOT_PREFIX") or ";"

activity = discord.Game(f"{prefix}help | bot.breq.dev")
breqbot = commands.Bot(
    prefix,
    description="Hi, I'm Breqbot! Beep boop :robot:",
    activity=activity
)

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
breqbot.load_extension("extensions.comics.xkcd")
breqbot.load_extension("extensions.comics.animegirl")

# - Fun
breqbot.load_extension("extensions.fun.fun")

# - Portal
breqbot.load_extension("extensions.apps.portal")

# - Lookup
breqbot.load_extension("extensions.lookup.minecraft")
breqbot.load_extension("extensions.lookup.vex")
breqbot.load_extension("extensions.lookup.scraper")

# - Configuration
breqbot.load_extension("extensions.config.allowlist")
breqbot.load_extension("extensions.config.rolemenu")

# - Watch
breqbot.load_extension("extensions.apps.watch")

# - Utility
breqbot.load_extension("extensions.utility.help_command")
breqbot.load_extension("extensions.utility.error_handler")
breqbot.load_extension("extensions.utility.guild_watch")


breqbot.run(os.getenv("DISCORD_TOKEN"))
