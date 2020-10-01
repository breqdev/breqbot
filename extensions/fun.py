import discord
from discord.ext import commands

from .utils import *

class Fun(BaseCog):
    "Miscellaneous fun commands"

    @commands.command()
    @commands.guild_only()
    @passfail
    async def poll(self, ctx, question, *answers):
        "Run a poll to vote for your favorite answers!"

        embed = discord.Embed(title=f"Poll: **{question}**")

        numbers = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        choices = {numbers[i]: answer for i, answer in enumerate(answers)}

        embed.description = "\n".join(f"{emoji}: {answer}" for emoji, answer in choices.items())

        message = await ctx.send(embed=embed)

        for emoji in choices:
            await message.add_reaction(emoji)

        return NoReact

def setup(bot):
    bot.add_cog(Fun(bot))
