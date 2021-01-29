import os
import re
import dataclasses
import typing

import discord
from discord.ext import commands
from fuzzywuzzy import process


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis


async def config_only(ctx):
    if not ctx.guild:
        return False
    return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
            and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))


class FuzzyMember(commands.Converter):
    async def convert(self, ctx, argument):
        "Attempt to match a string to a member of a guild."

        text = re.sub(r'\W+', '', argument)

        # It might be a mention or a user ID
        if text.isdigit():
            member = ctx.guild.get_member(int(text))
            if member:
                return member

        # Otherwise try to match based on string content
        member_names = {}
        for member in ctx.guild.members:
            member_names[member.display_name] = member

        match, score = process.extractOne(text, member_names.keys())

        if score > 80:
            return member_names[match]


@dataclasses.dataclass
class Response:
    """Class to represent a prepared Discord message that can be sent."""
    content: str = None
    files: dict = None
    embed: discord.Embed = None

    async def send_to(self, dest: typing.Union[discord.abc.Messageable,
                                               discord.Message]):

        if self.files:
            for file in self.files.values():
                file.seek(0)

            files = [discord.File(content, filename=name)
                     for name, content in self.files.items()]
            file_groups = [files[i:i+10] for i in range(0, len(files), 10)]
        else:
            files = []
            file_groups = []

        if isinstance(dest, discord.Message):
            await dest.edit(
                content=self.content, files=files, embed=self.embed)
            return dest

        if len(file_groups) == 0:
            return await dest.send(content=self.content, embed=self.embed)
        elif len(file_groups) == 1:
            return await dest.send(
                content=self.content, embed=self.embed, files=file_groups[0])
        else:
            # Send the first message with the content
            await dest.send(content=self.content, files=file_groups[0])
            # Send the middle messages with just files
            for group in file_groups[1:-1]:
                await dest.send(files=group)
            # Send the final message with the embed
            return await dest.send(embed=self.embed, files=file_groups[-1])


def is_nsfw():
    async def check(ctx):
        if ctx.channel.is_nsfw():
            return True
        if int(await ctx.bot.redis.get(
                f"channel:{ctx.guild.id}:{ctx.channel.id}:nsfw") or "0"):
            return True
        return False
    return commands.check(check)
