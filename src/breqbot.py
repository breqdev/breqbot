import os

import discord
from discord.ext import commands
import dotenv

dotenv.load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

breqbot = commands.Bot(";")

@breqbot.event
async def on_ready():
    print("Logged in as ")

@breqbot.command()
async def ping(ctx):
    await ctx.send(f"pong! {breqbot.latency}s")

breqbot.run(DISCORD_TOKEN)
