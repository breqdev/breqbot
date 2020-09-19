import os
import typing

import redis
import discord
from discord.ext import commands

prefix = os.getenv("BOT_PREFIX") or ";"

activity = discord.Game(f"{prefix}help")
breqbot = commands.Bot(prefix, description="Hi, I'm Breqbot! Beep boop :robot:", activity=activity)

breqbot.redis = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

breqbot.load_extension("cogs.reddit")
breqbot.load_extension("cogs.currency")
breqbot.load_extension("cogs.info")
breqbot.load_extension("cogs.inventory")
breqbot.load_extension("cogs.quests")
breqbot.load_extension("cogs.wear")
breqbot.load_extension("cogs.minecraft")
breqbot.load_extension("cogs.soundboard")
breqbot.load_extension("cogs.help_command")


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

@breqbot.event
async def on_command_error(ctx, exception):
    if isinstance(exception, commands.MissingRequiredArgument):
        error_message = await ctx.send(f"Missing required argument: {exception.param}")

    elif isinstance(exception, commands.ArgumentParsingError):
        error_message = await ctx.send("Argument parsing error")

    elif isinstance(exception, commands.BadArgument) or isinstance(exception, commands.BadUnionArgument):
        error_message = await ctx.send("Bad argument")

    elif isinstance(exception, commands.CheckFailure):
        error_message = await ctx.send(exception)

    elif isinstance(exception, commands.CommandNotFound):
        await ctx.message.add_reaction("🤔")
        return # command might belong to a different bot
        #error_message = await ctx.send("Command not found!")
    else:
        print(exception)
        error_message = await ctx.send(f"Error: {exception}")
        await ctx.message.add_reaction("⚠️")
        # await error_message.delete(delay=5)
        return

    await ctx.message.add_reaction("🚫")
    # await error_message.delete(delay=10)

breqbot.run(os.getenv("DISCORD_TOKEN"))
