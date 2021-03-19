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
breqbot.load_extension("bot.about.about")
breqbot.load_extension("bot.about.fun")
breqbot.load_extension("bot.about.config")
breqbot.load_extension("bot.about.debug")
breqbot.load_extension("bot.about.global_config")

# Profile
breqbot.load_extension("bot.profile.card")
# breqbot.load_extension("bot.profile.birthdays")
# breqbot.load_extension("bot.profile.pronouns")
breqbot.load_extension("bot.profile.outfit")

# Economy
breqbot.load_extension("bot.economy.currency")
breqbot.load_extension("bot.economy.items")
breqbot.load_extension("bot.economy.shop")

# Games
breqbot.load_extension("bot.games.games")

# Feeds
breqbot.load_extension("bot.feeds.reddit")
breqbot.load_extension("bot.feeds.comics")
breqbot.load_extension("bot.feeds.minecraft")
breqbot.load_extension("bot.feeds.youtube")
breqbot.load_extension("bot.feeds.stocks")
breqbot.load_extension("bot.feeds.forex")
# breqbot.load_extension("bot.feeds.status")
breqbot.load_extension("bot.feeds.watching")

# Tools
breqbot.load_extension("bot.tools.rolemenu")
breqbot.load_extension("bot.tools.emojiboard")
breqbot.load_extension("bot.tools.soundboard")

# Connections
# breqbot.load_extension("bot.connections.friendly_bots")
breqbot.load_extension("bot.connections.portal")

# Internal
breqbot.load_extension("bot.internal.help_command")
breqbot.load_extension("bot.internal.error_handler")
breqbot.load_extension("bot.internal.guild_watch")


breqbot.run(os.getenv("DISCORD_TOKEN"))
