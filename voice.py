import discord
from discord.ext import commands

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice = None

    @commands.command()
    async def join(self, ctx):
        "Join a voice channel"
        if ctx.guild is None:
            return # no voice channel on DMs

        if ctx.author.voice is None:
            return

        if ctx.author.voice.channel is None:
            return

        if self.voice:
            await self.voice.move_to(ctx.author.voice.channel)
        else:
            self.voice = await ctx.author.voice.channel.connect()

    @commands.command()
    async def leave(self, ctx):
        "Leave the current voice channel."
        if self.voice:
            await self.voice.disconnect()
        self.voice = None

    @commands.command()
    async def play(self, ctx, sound: str):
        "Play the designated sound."
        if not self.voice:
            return
        audio_src = discord.FFmpegOpusAudio(sound)
        self.voice.play(audio_src)

def setup(bot):
    bot.add_cog(Voice(bot))
