import asyncio
import re
import urllib.parse

import discord
from discord.ext import commands

import emoji
import youtube_dl

from .. import emoji_utils

from . import game

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


class Soundboard(game.Game):
    desc = "Play sounds in the voice channel!"

    def extract_id(self, url):
        "Extract the video ID from a YouTube URL"

        if "//" not in url:
            url = "https://" + url

        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise commands.CommandError(
                f"Invalid URL scheme: {parsed.scheme}")

        if parsed.netloc not in ("www.youtube.com",
                                 "youtu.be",
                                 "youtube.com",
                                 "www.youtu.be",
                                 "www.youtube-nocookie.com",
                                 "youtube-nocookie.com"):
            raise commands.CommandError(
                f"Not a YouTube url: {parsed.netloc}")

        if parsed.netloc in ("youtu.be", "www.youtu.be"):
            # Shortened URL
            id = parsed.path.lstrip("/")
        else:
            # Long URL
            if parsed.path == "/watch":
                # Video URL
                qs = urllib.parse.parse_qs(parsed.query)
                if qs.get("v") is None:
                    raise commands.CommandError(
                        f"Video ID not specified: {qs}")
                id = qs["v"][0]
            elif parsed.path.startswith("/embed/"):
                # Embed URL
                id = parsed.path[len("/embed/"):]
            else:
                # URL not recognised
                raise commands.CommandError(
                    f"Invalid video path: {parsed.path}")

        # Verify that the parsed ID looks right
        if not bool(re.match(r"[A-Za-z0-9\-_]{11}", id)):
            raise commands.CommandError(f"Invalid video ID: {id}")

        return id

    def get_yt_title(self, id):
        try:
            metadata = ytdl.extract_info(id, download=False)
        except youtube_dl.utils.DownloadError:
            raise commands.CommandError(f"Invalid YouTube ID: {id}")
        return metadata["title"]

    async def init(self):
        if self.args:
            if self.args[0] == "new":
                await self.newsound(self.args[1], self.args[2])
            elif self.args[0] == "del":
                await self.delsound(self.args[1])
            elif self.args[0] == "list":
                await self.list()
            elif self.args[0] == "play":
                await self.play(self.args[1])
            self.running = False
        else:
            self.message = None
            self.running = True

    async def new_player(self, user):
        pass

    async def newsound(self, name: str, url: str):
        "Add a new sound from YouTube url :new:"

        id = self.extract_id(url)
        title = self.get_yt_title(id)

        await self.redis.hmset_dict(
            f"soundboard:sounds:{self.ctx.guild.id}:{name}",
            {
                "name": name,
                "youtube-id": id,
                "title": title
            })
        await self.redis.sadd(f"soundboard:sounds:{self.ctx.guild.id}", name)

        await self.ctx.message.add_reaction("✅")

    async def delsound(self, name: str):
        "Remove a sound :wastebasket:"
        if not await self.redis.sismember(
                f"soundboard:sounds:{self.ctx.guild.id}", name):
            raise commands.CommandError("Sound not found")

        await self.redis.srem(f"soundboard:sounds:{self.ctx.guild.id}", name)
        await self.redis.delete(
            f"soundboard:sounds:{self.ctx.guild.id}:{name}")

        await self.ctx.message.add_reaction("✅")

    async def list(self):
        "List enabled sounds :dividers:"
        embed = discord.Embed(title=f"Soundboard on {self.ctx.guild.name}")

        sound_names = await self.redis.smembers(
            f"soundboard:sounds:{self.ctx.guild.id}")

        sounds = {name: await self.redis.hgetall(
                    f"soundboard:sounds:{self.ctx.guild.id}:{name}")
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
        await self.ctx.send(embed=embed)

    async def get_voice(self):
        voice_state = self.ctx.author.voice
        if not voice_state or not voice_state.channel:
            raise commands.CommandError(
                "You are not connected to a voice channel!")

        return await voice_state.channel.connect()

    async def play(self, name: str):
        "Play a sound"
        sound = await self.redis.hgetall(
            f"soundboard:sounds:{self.ctx.guild.id}:{name}")

        if not sound:
            raise commands.CommandError(f"Invalid sound {name}")

        async with SoundClient(self.ctx) as client:
            await client.play_sound(sound["youtube-id"])

    async def draw(self):
        if self.message:
            return

        message = await self.ctx.send(emoji_utils.text_to_emoji("Soundboard"))

        sound_names = await self.redis.smembers(
            f"soundboard:sounds:{self.ctx.guild.id}")
        for name in sound_names:
            if name in emoji.UNICODE_EMOJI:
                await message.add_reaction(name)
        await message.add_reaction("❌")

        self.client = SoundClient(self.ctx)
        await self.client.connect()

        self.message = message
        return message

    async def move(self, user, emoji):
        if emoji == "❌":
            await self.message.clear_reactions()
            await self.stop()
        if await self.redis.sismember(
                f"soundboard:sounds:{self.ctx.guild.id}", emoji):

            sound = await self.redis.hgetall(
                f"soundboard:sounds:{self.ctx.guild.id}:{emoji}")
            await self.client.play_sound(sound["youtube-id"])

    async def timeout(self):
        await self.stop()

    async def stop(self):
        await self.client.disconnect()
        await self.message.clear_reactions()
        self.running = False
