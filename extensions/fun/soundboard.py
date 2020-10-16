import asyncio
import re
import urllib.parse

import discord
from discord.ext import commands

import emoji
import youtube_dl

from ..base import BaseCog, UserError
from .. import emoji_utils

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options),
                   data=data)


class SoundClient():
    def __init__(self, ctx):
        voice_state = ctx.author.voice
        if not voice_state or not voice_state.channel:
            raise UserError("You are not connected to a voice channel!")

        self.channel = voice_state.channel
        self.playing = False

    @property
    def guild_id(self):
        return self.channel.guild.id

    async def __aenter__(self):
        try:
            self.device = await self.channel.connect()
        except discord.ClientException:
            raise UserError(
                "Breqbot is already connected to a voice channel!")
        else:
            return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.device.disconnect()

    async def play_sound(self, id):
        while self.playing:
            await asyncio.sleep(0.5)
        self.playing = True

        player = await YTDLSource.from_url(
            id, stream=True)

        def on_sound_finish(error):
            self.playing = False
            if error:
                raise error

        self.device.play(player, after=on_sound_finish)

        while self.playing:
            await asyncio.sleep(0.1)

        await asyncio.sleep(1)


class Soundboard(BaseCog):
    "Play sounds in the voice channel!"

    def extract_id(self, url):
        "Extract the video ID from a YouTube URL"

        if "//" not in url:
            url = "https://" + url

        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise UserError(f"Invalid URL scheme: {parsed.scheme}")

        if parsed.netloc not in ("www.youtube.com",
                                 "youtu.be",
                                 "youtube.com",
                                 "www.youtu.be",
                                 "www.youtube-nocookie.com",
                                 "youtube-nocookie.com"):
            raise UserError(f"Not a YouTube url: {parsed.netloc}")

        if parsed.netloc in ("youtu.be", "www.youtu.be"):
            # Shortened URL
            id = parsed.path.lstrip("/")
        else:
            # Long URL
            if parsed.path == "/watch":
                # Video URL
                qs = urllib.parse.parse_qs(parsed.query)
                if qs.get("v") is None:
                    raise UserError(f"Video ID not specified: {qs}")
                id = qs["v"][0]
            elif parsed.path.startswith("/embed/"):
                # Embed URL
                id = parsed.path[len("/embed/"):]
            else:
                # URL not recognised
                raise UserError(f"Invalid video path: {parsed.path}")

        # Verify that the parsed ID looks right
        if not bool(re.match(r"[A-Za-z0-9\-_]{11}", id)):
            raise UserError(f"Invalid video ID: {id}")

        return id

    def get_yt_title(self, id):
        try:
            metadata = ytdl.extract_info(id, download=False)
        except youtube_dl.utils.DownloadError:
            raise UserError(f"Invalid YouTube ID: {id}")
        return metadata["title"]

    @commands.command()
    @commands.guild_only()
    async def newsound(self, ctx, name: str, url: str):
        "Add a new sound from YouTube url :new:"

        id = self.extract_id(url)
        title = self.get_yt_title(id)

        self.redis.hset(f"soundboard:sounds:{ctx.guild.id}:{name}",
                        mapping={
                            "name": name,
                            "youtube-id": id,
                            "title": title
                        })
        self.redis.sadd(f"soundboard:sounds:{ctx.guild.id}", name)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def delsound(self, ctx, name: str):
        "Remove a sound :wastebasket:"
        if not self.redis.sismember(f"soundboard:sounds:{ctx.guild.id}", name):
            raise UserError("Sound not found")

        self.redis.srem(f"soundboard:sounds:{ctx.guild.id}", name)
        self.redis.delete(f"soundboard:sounds:{ctx.guild.id}:{name}")

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def sounds(self, ctx):
        "List enabled sounds :dividers:"
        embed = discord.Embed(title=f"Soundboard on {ctx.guild.name}")

        sound_names = self.redis.smembers(f"soundboard:sounds:{ctx.guild.id}")

        sounds = {name: self.redis.hgetall("soundboard:sounds:"
                                           f"{ctx.guild.id}:{name}")
                  for name in sound_names}

        if sounds:
            embed.description = "\n".join(
                f"{name}: {sound['title']} "
                + f"[({sound['youtube-id']})]"
                + f"(https://youtu.be/{sound['youtube-id']})"
                for name, sound in sounds.items())
        else:
            embed.description = ("The soundboard is currently empty. Try a "
                                 f"`{self.bot.main_prefix}newsound` ?")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def sound(self, ctx, name: str):
        "Play a sound"
        sound = self.redis.hgetall(
            f"soundboard:sounds:{ctx.guild.id}:{name}")

        if not sound:
            raise UserError(f"Invalid sound {name}")

        async with SoundClient(ctx) as client:
            await client.play_sound(sound["youtube-id"])

    @commands.command()
    @commands.guild_only()
    async def soundboard(self, ctx):
        "React to the soundboard to play sounds :control_knobs:"

        message = await ctx.send(emoji_utils.text_to_emoji("Soundboard"))

        sound_names = self.redis.smembers(f"soundboard:sounds:{ctx.guild.id}")
        for name in sound_names:
            if name in emoji.UNICODE_EMOJI:
                await message.add_reaction(name)
        await message.add_reaction("❌")

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id != self.bot.user.id)

        async with SoundClient(ctx) as client:
            while True:
                try:
                    reaction, user = await self.bot.wait_for(
                        "reaction_add", timeout=120, check=check)
                    await reaction.remove(user)
                except asyncio.TimeoutError:
                    return
                else:
                    if reaction.emoji == "❌":
                        await message.clear_reactions()
                        return
                    if self.redis.sismember(
                            f"soundboard:sounds:{ctx.guild.id}",
                            reaction.emoji):

                        sound = self.redis.hgetall(
                            "soundboard:sounds:"
                            f"{ctx.guild.id}:{reaction.emoji}")
                        await client.play_sound(sound["youtube-id"])

        await message.clear_reactions()


def setup(bot):
    bot.add_cog(Soundboard(bot))
