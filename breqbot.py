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

# General
breqbot.load_extension("extensions.info")

# Economy
breqbot.load_extension("extensions.economy.website")
breqbot.load_extension("extensions.economy.currency")
breqbot.load_extension("extensions.economy.inventory")
breqbot.load_extension("extensions.economy.items")
breqbot.load_extension("extensions.economy.quests")
breqbot.load_extension("extensions.economy.wear")

# Apps
breqbot.load_extension("extensions.apps.games")
breqbot.load_extension("extensions.apps.soundboard")
breqbot.load_extension("extensions.apps.rolemenu")
breqbot.load_extension("extensions.apps.portal")

# Feeds
# breqbot.load_extension("extensions.reddit")
# breqbot.load_extension("extensions.minecraft")
# breqbot.load_extension("extensions.vex")
# breqbot.load_extension("extensions.comics")
# breqbot.load_extension("extensions.fun")
# breqbot.load_extension("extensions.watcher")

# Utility
breqbot.load_extension("extensions.utility.help_command")
breqbot.load_extension("extensions.utility.error_handler")
breqbot.load_extension("extensions.utility.guild_watch")

breqbot.run(os.getenv("DISCORD_TOKEN"))
