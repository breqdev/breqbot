import os

import redis
import discord
from discord.ext import commands

activity = discord.Game(";help")
breqbot = commands.Bot(";", description="Hi, I'm Breqbot! Beep boop :robot:", activity=activity)

breqbot.redis = redis.Redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)

breqbot.load_extension("reddit")
breqbot.load_extension("currency")
breqbot.load_extension("debug")

import help_command
breqbot.help_command = help_command.HelpCommand()

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

@breqbot.command()
async def website(ctx):
    "Link to the bot's website!"
    await ctx.send(os.getenv("WEBSITE")+str(ctx.guild.id))

breqbot.run(os.getenv("DISCORD_TOKEN"))
