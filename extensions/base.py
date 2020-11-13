import os

from discord.ext import commands


class BaseCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    @staticmethod
    async def config_only(ctx):
        if not ctx.guild:
            return False
        return (ctx.guild.id == int(os.getenv("CONFIG_GUILD"))
                and ctx.channel.id == int(os.getenv("CONFIG_CHANNEL")))

    @staticmethod
    async def pack_send(dest, content, files, embed):
        file_groups = [files[i:i+10] for i in range(0, len(files), 10)]

        if len(file_groups) == 0:
            await dest.send(content=content, embed=embed)
        elif len(file_groups) == 1:
            await dest.send(content=content, embed=embed, files=file_groups[0])
        else:
            # Send the first message with the content
            await dest.send(content=content, files=file_groups[0])
            # Send the middle messages with just files
            for group in file_groups[1:-1]:
                await dest.send(files=group)
            # Send the final message with the embed
            await dest.send(embed=embed, files=file_groups[-1])
