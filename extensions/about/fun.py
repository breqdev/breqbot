import random
import asyncio

import discord
from discord.ext import commands
from discord_slash import cog_ext, SlashCommandOptionType
from discord_slash.utils import manage_commands

from .. import emoji_utils, slash


class Fun(slash.SlashCog):
    "Miscellaneous fun commands"

    category = "About"

    @cog_ext.cog_slash(
        name="say",
        description="Repeat after me!",
        guild_ids=[748012955404337296],
        options=[
            manage_commands.create_option(
                name="message",
                description="Message to repeat",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def say(self, ctx, message: str):
        "Repeat after me!"
        await ctx.send(content=discord.utils.escape_mentions(message))

    @cog_ext.cog_slash(
        name="poll",
        description="Run a poll to vote for your favorite answers!",
        guild_ids=[748012955404337296],
        options=[
            manage_commands.create_option(
                name="question",
                description="Question to ask",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ] + [
            manage_commands.create_option(
                name=f"option{n}",
                description=f"Response number {n}",
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
            for n in range(1, 5)
        ]
    )
    @commands.guild_only()
    async def poll(self, ctx, question: str,
                   option1: str = None, option2: str = None,
                   option3: str = None, option4: str = None):
        "Run a poll to vote for your favorite answers!"

        answers = [option for option in (option1, option2, option3, option4)
                   if option is not None]

        await ctx.send(content=f"Poll: **{question}**")

        embed = discord.Embed()

        numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
                   "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        choices = {numbers[i]: answer for i, answer in enumerate(answers)}

        embed.description = "\n".join(f"{emoji}: {answer}"
                                      for emoji, answer in choices.items())

        message = await ctx.channel.send(embed=embed)

        for emoji in choices:
            await message.add_reaction(emoji)

    @cog_ext.cog_slash(
        name="8ball",
        description="Ask the magic 8 ball...",
        guild_ids=[748012955404337296],
        options=[
            manage_commands.create_option(
                name="question",
                description="Question to ask the magic 8 ball",
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
        ]
    )
    async def eightball(self, ctx, message: str):
        "Ask the magic 8 ball..."

        await ctx.send(content=("The 8 ball says... "
                                ":8ball: ~~*shake shake*~~..."))
        await asyncio.sleep(5)

        response = random.choice(["YES", "NO", "MAYBE"])
        await ctx.edit(content=("The 8 ball says... "
                                f":8ball: **{response}**"))

    @cog_ext.cog_slash(
        name="emoji",
        description="Write text in 🇧 🇮 🇬 letters",
        guild_ids=[748012955404337296],
        options=[
            manage_commands.create_option(
                name="message",
                description="Message to biggify",
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def emoji(self, ctx, text: str):
        "Write text in 🇧 🇮 🇬 letters"

        text = emoji_utils.text_to_emoji(text)
        await ctx.send(text or "\u200b")


def setup(bot):
    bot.add_cog(Fun(bot))
