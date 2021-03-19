import asyncio

import emoji
import discord
from discord.ext import commands

from bot import base
from bot import emoji_utils

SOUND_FILES = ["wav", "mp3"]


class SoundClient():
    def __init__(self, ctx):
        voice_state = ctx.author.voice
        if not voice_state or not voice_state.channel:
            raise commands.CommandError(
                "You are not connected to a voice channel!")

        self.channel = voice_state.channel
        self.playing = False

    @property
    def guild_id(self):
        return self.channel.guild.id

    async def connect(self):
        try:
            self.device = await self.channel.connect()
        except discord.ClientException:
            raise commands.CommandError(
                "Breqbot is already connected to a voice channel!")

    async def __aenter__(self):
        await self.connect()
        return self

    async def disconnect(self):
        await self.device.disconnect()

    async def __aexit__(self, exc_type, exc, tb):
        await self.disconnect()

    async def play_sound(self, url):
        if self.device.is_playing():
            return
        player = discord.FFmpegPCMAudio(url)
        self.device.play(player)


class Soundboard(base.BaseCog):
    description = "Play custom sounds in a voice channel"
    category = "Tools"

    async def get_sound_file(self, ctx):
        for attachment in ctx.message.attachments:
            if attachment.filename.split(".")[-1] in SOUND_FILES:
                return attachment
        else:
            raise commands.CommandError("You need to attach an audio file!")

    @commands.group(invoke_without_command=True)
    async def soundboard(self, ctx):
        "Display the soundboard"
        message = await ctx.send(emoji_utils.text_to_emoji("Soundboard"))

        sound_names = await self.redis.smembers(
            f"soundboard:sounds:{ctx.guild.id}")
        for name in sound_names:
            if name in emoji.UNICODE_EMOJI:
                await message.add_reaction(name)
        await message.add_reaction("❌")

        client = SoundClient(ctx)
        await client.connect()

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id != self.bot.user.id)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=3600, check=check)
            except asyncio.TimeoutError:
                return
            else:
                if reaction.emoji == "❌":
                    await message.clear_reactions()
                    await client.disconnect()
                if await self.redis.sismember(
                        f"soundboard:sounds:{ctx.guild.id}", reaction.emoji):

                    sound = await self.redis.hgetall(
                        f"soundboard:sounds:{ctx.guild.id}:{reaction.emoji}")
                    await client.play_sound(sound["url"])
                await reaction.remove(user)

    @soundboard.command()
    async def add(self, ctx, emoji: str):
        "Add a new sound :new:"
        sound = await self.get_sound_file(ctx)

        await self.redis.hmset_dict(
            f"soundboard:sounds:{ctx.guild.id}:{emoji}",
            {
                "name": emoji,
                "url": sound.url,
                "title": sound.filename
            })
        await self.redis.sadd(f"soundboard:sounds:{ctx.guild.id}", emoji)

        await ctx.message.add_reaction("✅")

    @soundboard.command()
    async def remove(self, ctx, emoji: str):
        "Remove a sound :wastebasket:"
        if not await self.redis.sismember(
                f"soundboard:sounds:{ctx.guild.id}", emoji):
            raise commands.CommandError("Sound not found")

        await self.redis.srem(f"soundboard:sounds:{ctx.guild.id}", emoji)
        await self.redis.delete(
            f"soundboard:sounds:{ctx.guild.id}:{emoji}")

        await ctx.message.add_reaction("✅")

    @soundboard.command()
    async def list(self, ctx):
        "List enabled sounds :dividers:"
        embed = discord.Embed(title=f"Soundboard on {ctx.guild.name}")

        sound_names = await self.redis.smembers(
            f"soundboard:sounds:{ctx.guild.id}")

        sounds = {name: await self.redis.hgetall(
                    f"soundboard:sounds:{ctx.guild.id}:{name}")
                  for name in sound_names}

        if sounds:
            embed.description = "\n".join(
                f"{name}: [{sound['title']}]"
                + f"({sound['url']})"
                for name, sound in sounds.items())
        else:
            embed.description = ("The soundboard is currently empty. Try a "
                                 f"`{self.bot.main_prefix}soundboard add` ?")
        await ctx.send(embed=embed)

    @soundboard.command()
    async def play(self, ctx, emoji: str):
        "Play a sound"

        sound = await self.redis.hgetall(
            f"soundboard:sounds:{ctx.guild.id}:{emoji}")

        if not sound:
            raise commands.CommandError(f"Invalid sound {emoji}")

        async with SoundClient(ctx) as client:
            await client.play_sound(sound["url"])


def setup(bot):
    bot.add_cog(Soundboard(bot))
