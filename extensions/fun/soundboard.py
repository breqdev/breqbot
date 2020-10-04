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


class Soundboard(BaseCog):
    "Play sounds in the voice channel!"
    def __init__(self, bot):
        super().__init__(bot)
        self.clients = {}

    @commands.command()
    @commands.guild_only()
    async def join(self, ctx):
        "Enter a voice channel :loud_sound:"
        user = ctx.author
        voice_state = user.voice

        if not voice_state or not voice_state.channel:
            raise UserError(f"{user.mention} is not in a voice channel!")

        channel = voice_state.channel

        self.clients[ctx.guild.id] = client = await channel.connect()

        # Public API doesn't expose deafen function, do something hacky
        await client.main_ws.voice_state(ctx.guild.id, channel.id,
                                         self_deaf=True)

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def leave(self, ctx):
        "Leave a voice channel :mute:"
        if self.clients.get(ctx.guild.id) is None:
            raise UserError("Not connected to a channel!")

        await self.clients[ctx.guild.id].disconnect()
        del self.clients[ctx.guild.id]

        await ctx.message.add_reaction("✅")

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
    async def listsounds(self, ctx):
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

    async def play_sound(self, guild_id, id):
        if not self.clients.get(guild_id):
            raise UserError("Not connected to voice.")

        while self.clients[guild_id].is_playing():
            await asyncio.sleep(0.5)
        player = await YTDLSource.from_url(id, loop=self.bot.loop, stream=True)
        self.clients[guild_id].play(
            player, after=lambda e: print(f"Player error: {e}") if e else None)

    @commands.command()
    @commands.guild_only()
    async def play(self, ctx, name: str):
        "Play a sound :arrow_forward:"
        if not self.redis.sismember(f"soundboard:sounds:{ctx.guild.id}", name):
            raise UserError("Sound not found")
        sound = self.redis.hgetall(f"soundboard:sounds:{ctx.guild.id}:{name}")

        await self.play_sound(ctx.guild.id, sound["youtube-id"])
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    async def soundboard(self, ctx):
        "React to the soundboard to play sounds :control_knobs:"

        client = self.clients.get(ctx.guild.id)
        if client is None:
            raise UserError("Not connected to voice.")

        message = await ctx.send(emoji_utils.text_to_emoji("Soundboard"))
        # await message.add_reaction("➡️")

        sound_names = self.redis.smembers(f"soundboard:sounds:{ctx.guild.id}")
        for name in sound_names:
            if name in emoji.UNICODE_EMOJI:
                await message.add_reaction(name)

        def check(reaction, user):
            return (reaction.message.id == message.id
                    and user.id != self.bot.user.id)

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    "reaction_add", timeout=120, check=check)
                await reaction.remove(user)
            except asyncio.TimeoutError:
                return
            else:
                if (self.clients.get(ctx.guild.id)
                        and self.redis.sismember(
                            f"soundboard:sounds:{ctx.guild.id}",
                            reaction.emoji)):
                    sound = self.redis.hgetall(
                        f"soundboard:sounds:{ctx.guild.id}:{reaction.emoji}")
                    await self.play_sound(ctx.guild.id, sound["youtube-id"])


def setup(bot):
    bot.add_cog(Soundboard(bot))
