import os

import discord
from discord.ext import commands

activity = discord.Game(";help")
breqbot = commands.Bot(";", description="Hi, I'm Breqbot! Beep boop :robot:", activity=activity)

breqbot.load_extension("reddit")
breqbot.load_extension("debug")

import help_command
breqbot.help_command = help_command.HelpCommand()

breqbot.run(os.getenv("DISCORD_TOKEN"))
