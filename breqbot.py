import os
import typing

import redis
import discord
from discord.ext import commands

prefix = os.getenv("BOT_PREFIX") or ";"

activity = discord.Game(f"{prefix}help")
breqbot = commands.Bot(prefix, description="Hi, I'm Breqbot! Beep boop :robot:", activity=activity)

breqbot.redis = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

breqbot.load_extension("reddit")
breqbot.load_extension("currency")
breqbot.load_extension("debug")
breqbot.load_extension("inventory")
breqbot.load_extension("quests")
breqbot.load_extension("wear")
breqbot.load_extension("help_command")


@breqbot.event
async def on_ready():
    breqbot.redis.delete("guild:list")
    breqbot.redis.sadd("guild:list", *(guild.id for guild in breqbot.guilds))

    # Cache of guild ID -> name, guild member list, user ID -> name, etc
    for guild in breqbot.guilds:
        breqbot.redis.set(f"guild:name:{guild.id}", guild.name)

        breqbot.redis.delete(f"guild:member:{guild.id}")
        breqbot.redis.sadd(f"guild:member:{guild.id}", *(member.id for member in guild.members))

    for member in breqbot.get_all_members():
        breqbot.redis.set(f"user:name:{member.id}", member.name)

@breqbot.event
async def on_member_join(member):
    breqbot.redis.sadd(f"guild:member:{member.guild.id}", member.id)

@breqbot.event
async def on_member_leave(member):
    breqbot.redis.srem(f"guild:member:{member.guild.id}", member.id)

@breqbot.event
async def on_guild_join(guild):
    breqbot.redis.sadd("guild:list", guild.id)
    breqbot.redis.set(f"guild:name:{guild.id}", guild.name)

    breqbot.redis.delete(f"guild:member:{guild.id}")
    breqbot.redis.sadd(f"guild:member:{guild.id}", *(member.id for member in guild.members))

@breqbot.event
async def on_guild_leave(guild):
    breqbot.redis.srem("guild:list", guild.id)
    breqbot.redis.delete(f"guild:name:{guild.id}")
    breqbot.redis.delete(f"guild:member:{guild.id}")

@breqbot.command()
async def website(ctx, user: typing.Optional[discord.User]):
    "Link to the bot's website!"
    if user:
        await ctx.send(f"{os.getenv('WEBSITE')}user/{ctx.guild.id}/{user.id}")
    else:
        await ctx.send(f"{os.getenv('WEBSITE')}server/{ctx.guild.id}")

@breqbot.command()
async def testing(ctx):
    "Come join the bot testing server to suggest features and discuss Breqbot!"
    await ctx.send("Join us and discuss features for Breqbot!")
    await ctx.send(os.getenv("TESTING_DISCORD"))

breqbot.run(os.getenv("DISCORD_TOKEN"))
