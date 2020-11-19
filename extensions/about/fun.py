import random
import asyncio

import discord
from discord.ext import commands

from .. import base, emoji_utils


class Fun(base.BaseCog):
    "Miscellaneous fun commands"

    @commands.command()
    async def say(self, ctx, *, message: str):
        "Repeat after me!"
        await ctx.send(discord.utils.escape_mentions(message))

    @commands.command()
    @commands.guild_only()
    async def poll(self, ctx, question: str, *answers: str):
        "Run a poll to vote for your favorite answers!"

        if len(answers) > 10:
            raise commands.CommandError(
                'Polls are limited to 10 options. '
                'Did you remember to use quotes? e.g.\n'
                f'`{self.bot.main_prefix}poll '
                '"my question" "option 1" "option 2"...`')

        embed = discord.Embed(title=f"Poll: **{question}**")

        numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣",
                   "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        choices = {numbers[i]: answer for i, answer in enumerate(answers)}

        embed.description = "\n".join(f"{emoji}: {answer}"
                                      for emoji, answer in choices.items())

        message = await ctx.send(embed=embed)

        for emoji in choices:
            await message.add_reaction(emoji)

    @commands.command(name="8ball")
    async def eightball(self, ctx):
        "Ask the magic 8 ball..."

        message = await ctx.send("The 8 ball says... "
                                 ":8ball: ~~*shake shake*~~...")
        await asyncio.sleep(5)

        response = random.choice(["YES", "NO", "MAYBE"])
        await message.edit(content="The 8 ball says... "
                           f":8ball: **{response}**")

    @commands.command()
    async def emoji(self, ctx, *, text: str):
        "Write text in 🇧 🇮 🇬 letters"

        text = emoji_utils.text_to_emoji(text)
        await ctx.send(text or "\u200b")


def setup(bot):
    bot.add_cog(Fun(bot))
