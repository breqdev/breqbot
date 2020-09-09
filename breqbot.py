import os

import discord
from discord.ext import commands

activity = discord.Game(";help")
breqbot = commands.Bot(";", description="Hi, I'm Breqbot! Beep boop :robot:", activity=activity)

@breqbot.command()
async def foo(ctx):
    "super secret debugging stuff :shushing_face:"
    await ctx.channel.send("bar!")

import help_command
breqbot.help_command = help_command.HelpCommand()

import reddit
breqbot.add_cog(reddit.Reddit(breqbot))

breqbot.run(os.getenv("DISCORD_TOKEN"))
