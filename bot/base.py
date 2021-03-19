import os
import re
import dataclasses
import typing
import inspect

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


async def ctx_is_nsfw(ctx):
    if ctx.channel.is_nsfw():
        return True
    if int(await ctx.bot.redis.get(
            f"channel:{ctx.guild.id}:{ctx.channel.id}:nsfw") or "0"):
        return True
    return False


def is_nsfw():
    return commands.check(ctx_is_nsfw)


class SilentError(commands.CommandError):
    pass


class Prompt:
    def __init__(self, ctx, name):
        self.name = name
        self.client = ctx.bot
        self.ctx = ctx
        self.lines = []
        self.message = None

    async def append(self, line):
        self.lines.append(line)
        await self.update()

    async def edit(self, line):
        self.lines[-1] = line
        await self.update()

    async def update(self):
        if self.message is None:
            self.message = await self.ctx.send("\n".join(self.lines))
        else:
            await self.message.edit(content="\n".join(self.lines))

    async def __aenter__(self):
        await self.append(f"┏ **{self.name}** ")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if isinstance(exc, commands.CommandError):
            await self.append(f"┗ 🚫 {exc}")
            raise SilentError()
        elif exc:
            await self.append("┗ ⚠️")
        else:
            await self.append("┗ ✅")

    async def input(self, prompt, converter=str, current=None):
        if current:
            await self.append(f"┃ *{prompt}* (type `skip` for *{current}*)")
        else:
            await self.append(f"┃ *{prompt}*")

        def check(message):
            return (message.author == self.ctx.author
                    and message.channel == self.ctx.channel)

        message = await self.client.wait_for("message", check=check)

        if current and message.content == "skip":
            await self.edit(f"┃ *{prompt}* - *{current}* ")
            await message.delete()
            return current

        try:
            response = await self.ctx.command.do_conversion(
                self.ctx, converter, message.content,
                type("Param", (),
                     {"kind": inspect.Parameter.VAR_POSITIONAL})())
            # The hacky fake parameter object lets us use discord.py's built
            # in converter system to parse user inputs

            # The do_conversion method will raise BadArgument when applicable
            # and this will be handled and displayed nicely by __aexit__
        except Exception:
            raise
        else:
            await self.edit(f"┃ *{prompt}* - **{response}** ")
        finally:
            await message.delete()
        return response
