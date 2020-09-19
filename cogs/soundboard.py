import discord
from discord.ext import commands

class Soundboard(commands.Cog):
    "Play sounds in the voice channel!"

    def __init__(self, bot):
        self.bot = bot
        self.redis = bot.redis

    @commands.command()
    async def join(self, ctx):
        "Enter a voice channel"
        if not ctx.guild:
            return

        user = ctx.author
        voice_state = user.voice

        if not voice_state or not voice_state.channel:
            return

        channel = voice_state.channel

        self.channel = await channel.connect()

        # Public API doesn't expose deafen function, do something hacky
        await self.channel.main_ws.voice_state(ctx.guild.id, channel.id, self_deaf=True)

        await ctx.message.add_reaction("✅")

    @commands.command()
    async def leave(self, ctx):
        "Leave a voice channel"
        if not self.channel:
            return

        await self.channel.disconnect()
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def newsound(self, ctx, url: str):
        "Add a new sound from YouTube url"
        await ctx.send("Coming soon!")

    @commands.command()
    async def soundboard(self, ctx):
        "React to the soundboard to play sounds"
        await ctx.send("Coming soon!")

    @commands.command()
    async def listsounds(self, ctx):
        "List enabled sounds"
        await ctx.send("Coming soon!")

def setup(bot):
    bot.add_cog(Soundboard(bot))
