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

breqbot.watches = {}

# About
breqbot.load_extension("extensions.about.about")
breqbot.load_extension("extensions.about.fun")
breqbot.load_extension("extensions.about.config")
breqbot.load_extension("extensions.about.debug")
breqbot.load_extension("extensions.about.global_config")

# Profile
breqbot.load_extension("extensions.profile.card")
breqbot.load_extension("extensions.profile.birthdays")
breqbot.load_extension("extensions.profile.pronouns")
breqbot.load_extension("extensions.profile.outfit")

# Economy
breqbot.load_extension("extensions.economy.currency")
breqbot.load_extension("extensions.economy.items")
breqbot.load_extension("extensions.economy.shop")

# Games
breqbot.load_extension("extensions.games.games")

# Feeds
breqbot.load_extension("extensions.feeds.reddit")
breqbot.load_extension("extensions.feeds.comics")
breqbot.load_extension("extensions.feeds.minecraft")
breqbot.load_extension("extensions.feeds.youtube")
breqbot.load_extension("extensions.feeds.status")
breqbot.load_extension("extensions.feeds.watching")

# Tools
breqbot.load_extension("extensions.tools.rolemenu")
breqbot.load_extension("extensions.tools.emojiboard")

# Connections
breqbot.load_extension("extensions.connections.friendly_bots")
breqbot.load_extension("extensions.connections.portal")

# Internal
breqbot.load_extension("extensions.internal.help_command")
breqbot.load_extension("extensions.internal.error_handler")
breqbot.load_extension("extensions.internal.guild_watch")


breqbot.run(os.getenv("DISCORD_TOKEN"))
