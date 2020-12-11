import os
import re
import dataclasses
import typing
import urllib.parse

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


class MessageLink(commands.Converter):
    async def convert(self, ctx, argument):
        # Grab the guild, channel, message out of the message link, e.g.,
        # https://discordapp.com/channels/747905649303748678/747921216186220654/748237781519827114
        # or a bare message ID, e.g.
        # 748237781519827114

        if argument.startswith("https://discord.com/channels/"):
            message_id = int(
                urllib.parse.urlparse(argument).path.lstrip("/").split("/")[3])
        else:
            try:
                message_id = int(argument)
            except ValueError:
                raise commands.BadArgument("Invalid message ID")

        try:
            message = await ctx.fetch_message(message_id)
        except discord.NotFound:
            raise commands.BadArgument("Message not found")

        return message


@dataclasses.dataclass
class Response:
    """Class to represent a prepared Discord message that can be sent."""
    content: str
    files: dict
    embed: discord.Embed

    async def send_to(self, dest: typing.Union[discord.abc.Messageable,
                                               discord.Message]):

        files = [discord.File(content, filename=name)
                 for name, content in self.files.items()]
        file_groups = [files[i:i+10] for i in range(0, len(files), 10)]

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
