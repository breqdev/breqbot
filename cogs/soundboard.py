import discord
from discord.ext import commands

from .breqcog import Breqcog, passfail, Fail

class Soundboard(Breqcog):
    "Play sounds in the voice channel!"

    @commands.command()
    @passfail
    async def join(self, ctx):
        "Enter a voice channel"
        if not ctx.guild:
            raise Fail("Cannot join voice in DM")

        user = ctx.author
        voice_state = user.voice

        if not voice_state or not voice_state.channel:
            raise Fail(f"{user.mention} is not in a voice channel!")

        channel = voice_state.channel

        self.channel = await channel.connect()

        # Public API doesn't expose deafen function, do something hacky
        await self.channel.main_ws.voice_state(ctx.guild.id, channel.id, self_deaf=True)

    @commands.command()
    @passfail
    async def leave(self, ctx):
        "Leave a voice channel"
        if not self.channel:
            raise Fail("Not connected to a channel!")

        await self.channel.disconnect()

    @commands.command()
    @passfail
    async def newsound(self, ctx, url: str):
        "Add a new sound from YouTube url"
        return "Coming soon!"

    @commands.command()
    @passfail
    async def soundboard(self, ctx):
        "React to the soundboard to play sounds"
        return "Coming soon!"

    @commands.command()
    @passfail
    async def listsounds(self, ctx):
        "List enabled sounds"
        return "Coming soon!"

def setup(bot):
    bot.add_cog(Soundboard(bot))
