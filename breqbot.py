import os
import asyncio

import aioredis
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

loop = asyncio.get_event_loop()
breqbot.redis = loop.run_until_complete(aioredis.create_redis_pool(
    os.getenv("REDIS_URL"), encoding="utf-8"))


# About
breqbot.load_extension("extensions.about.about")
breqbot.load_extension("extensions.about.config")
breqbot.load_extension("extensions.about.global_config")

# Profile
breqbot.load_extension("extensions.profile.card")
breqbot.load_extension("extensions.profile.birthdays")
breqbot.load_extension("extensions.profile.pronouns")

# Economy
breqbot.load_extension("extensions.economy.currency")
breqbot.load_extension("extensions.economy.items")

# Games
breqbot.load_extension("extensions.games.fun")
breqbot.load_extension("extensions.games.games")

# Feeds
breqbot.load_extension("extensions.reddit.reddit")
breqbot.load_extension("extensions.comics.comics")
breqbot.load_extension("extensions.lookup.vex")
breqbot.load_extension("extensions.lookup.minecraft")

# Tools
breqbot.load_extension("extensions.config.rolemenu")

# Connections
breqbot.load_extension("extensions.utility.friendly_bots")
breqbot.load_extension("extensions.economy.portal")

# Internal
breqbot.load_extension("extensions.utility.help_command")
breqbot.load_extension("extensions.utility.error_handler")
breqbot.load_extension("extensions.utility.guild_watch")


breqbot.run(os.getenv("DISCORD_TOKEN"))
