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


# - General
breqbot.load_extension("extensions.info")
breqbot.load_extension("extensions.profile")

# Economy
breqbot.load_extension("extensions.economy.currency")
breqbot.load_extension("extensions.economy.items")
breqbot.load_extension("extensions.economy.portal")

# - Reddit
breqbot.load_extension("extensions.reddit.reddit")

# - Comics
breqbot.load_extension("extensions.comics.comics")

# - Fun
breqbot.load_extension("extensions.fun.fun")
breqbot.load_extension("extensions.fun.pronouns")

# - Lookup
breqbot.load_extension("extensions.lookup.vex")
breqbot.load_extension("extensions.lookup.minecraft")

# - Configuration
breqbot.load_extension("extensions.config.config")
breqbot.load_extension("extensions.config.rolemenu")

# - Utility
breqbot.load_extension("extensions.utility.help_command")
breqbot.load_extension("extensions.utility.error_handler")
breqbot.load_extension("extensions.utility.guild_watch")
breqbot.load_extension("extensions.utility.friendly_bots")
breqbot.load_extension("extensions.utility.global_config")


breqbot.run(os.getenv("DISCORD_TOKEN"))
