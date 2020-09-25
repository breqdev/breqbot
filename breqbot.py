import os
import typing

import redis
import discord
from discord.ext import commands

prefix = os.getenv("BOT_PREFIX") or ";"

activity = discord.Game(f"{prefix}help | breq.dev")
breqbot = commands.Bot(prefix, description="Hi, I'm Breqbot! Beep boop :robot:", activity=activity)

breqbot.redis = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

# General
breqbot.load_extension("extensions.info")

# External Features
breqbot.load_extension("extensions.reddit")
breqbot.load_extension("extensions.minecraft")
breqbot.load_extension("extensions.vex")
breqbot.load_extension("extensions.comics")

# Breqbot Features
breqbot.load_extension("extensions.soundboard")
breqbot.load_extension("extensions.portal")

# Economy/shop/outfits
breqbot.load_extension("extensions.website")
breqbot.load_extension("extensions.currency")
breqbot.load_extension("extensions.inventory")
breqbot.load_extension("extensions.quests")
breqbot.load_extension("extensions.wear")

# Utility
breqbot.load_extension("extensions.help_command")
breqbot.load_extension("extensions.guild_watch")

breqbot.run(os.getenv("DISCORD_TOKEN"))
