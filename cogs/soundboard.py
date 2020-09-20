import asyncio
import string
import re
import urllib.parse

import discord
from discord.ext import commands

import emoji
import youtube_dl

from .breqcog import Breqcog, passfail, Fail, NoReact

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
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
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
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Soundboard(Breqcog):
    "Play sounds in the voice channel!"
    def __init__(self, bot):
        super().__init__(bot)
        self.clients = {}

    @commands.command()
    @commands.guild_only()
    @passfail
    async def join(self, ctx):
        "Enter a voice channel"
        user = ctx.author
        voice_state = user.voice

        if not voice_state or not voice_state.channel:
            raise Fail(f"{user.mention} is not in a voice channel!")

        channel = voice_state.channel

        self.clients[ctx.guild.id] = client = await channel.connect()

        # Public API doesn't expose deafen function, do something hacky
        await client.main_ws.voice_state(ctx.guild.id, channel.id, self_deaf=True)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def leave(self, ctx):
        "Leave a voice channel"
        if self.clients.get(ctx.guild.id) is None:
            raise Fail("Not connected to a channel!")

        await self.clients[ctx.guild.id].disconnect()
        del self.clients[ctx.guild.id]

    def extract_id(self, url):
        "Extract the video ID from a YouTube URL"

        if "//" not in url:
            url = "https://" + url

        parsed = urllib.parse.urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise Fail(f"Invalid URL scheme: {parsed.scheme}")

        if parsed.netloc not in ("www.youtube.com",
                                 "youtu.be",
                                 "youtube.com",
                                 "www.youtu.be",
                                 "www.youtube-nocookie.com",
                                 "youtube-nocookie.com"):
            raise Fail(f"Not a YouTube url: {parsed.netloc}")

        if parsed.netloc in ("youtu.be", "www.youtu.be"):
            # Shortened URL
            id = parsed.path.lstrip("/")
        else:
            # Long URL
            if parsed.path == "/watch":
                # Video URL
                qs = urllib.parse.parse_qs(parsed.query)
                if qs.get("v") is None:
                    raise Fail(f"Video ID not specified: {qs}")
                id = qs["v"][0]
            elif parsed.path.startswith("/embed/"):
                # Embed URL
                id = parsed.path[len("/embed/"):]
            else:
                # URL not recognised
                raise Fail(f"Invalid video path: {parsed.path}")

        # Verify that the parsed ID looks right
        if not bool(re.match(r"[A-Za-z0-9\-_]{11}", id)):
            raise Fail(f"Invalid video ID: {id}")

        return id

    def get_yt_title(self, id):
        try:
            metadata = ytdl.extract_info(id, download=False)
        except youtube_dl.utils.DownloadError:
            raise Fail(f"Invalid YouTube ID: {id}")
        return metadata["title"]

    @commands.command()
    @commands.guild_only()
    @passfail
    async def newsound(self, ctx, emoji: str, url: str):
        "Add a new sound from YouTube url"

        id = self.extract_id(url)
        title = self.get_yt_title(id)

        self.redis.hset(f"soundboard:sounds:{ctx.guild.id}:{emoji}",
                        mapping={
                            "emoji": emoji,
                            "youtube-id": id,
                            "title": title
                        })
        self.redis.sadd(f"soundboard:sounds:{ctx.guild.id}", emoji)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def delsound(self, ctx, emoji: str):
        "Remove a sound"
        if not self.redis.sismember(f"soundboard:sounds:{ctx.guild.id}", emoji):
            raise Fail("Sound not found")

        self.redis.srem(f"soundboard:sounds:{ctx.guild.id}", emoji)
        self.redis.delete(f"soundboard:sounds:{ctx.guild.id}:{emoji}")

    @commands.command()
    @commands.guild_only()
    @passfail
    async def listsounds(self, ctx):
        "List enabled sounds"
        embed = discord.Embed(title=f"Soundboard on {ctx.guild.name}")

        emojis = self.redis.smembers(f"soundboard:sounds:{ctx.guild.id}")

        sounds = {emoji: self.redis.hgetall(f"soundboard:sounds:{ctx.guild.id}:{emoji}")
                  for emoji in emojis}

        if sounds:
            embed.description = "\n".join(f"{emoji}: {sound['title']} "
                                          + f"[({sound['youtube-id']})]"
                                          + f"(https://youtu.be/{sound['youtube-id']})"
                                          for emoji, sound in sounds.items())
        else:
            embed.description = f"The soundboard is currently empty. Try a `{self.bot.command_prefix}newsound` ?"
        return embed

    async def play_sound(self, guild_id, id):
        if not self.clients.get(guild_id):
            raise Fail("Not connected to voice.")

        while self.clients[guild_id].is_playing():
            asyncio.sleep(0.5)
        player = await YTDLSource.from_url(id, loop=self.bot.loop, stream=True)
        self.clients[guild_id].play(player, after=lambda e: print(f"Player error: {e}") if e else None)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def play(self, ctx, name: str):
        "Play a sound"
        if not self.redis.sismember(f"soundboard:sounds:{ctx.guild.id}", emoji):
            raise Fail("Sound not found")
        sound = self.redis.hgetall(f"soundboard:sounds:{ctx.guild.id}:{emoji}")

        await self.play_sound(ctx.guild.id, sound["youtube-id"])

    def text_to_emoji(self, text):
        emoji_text = []
        for letter in text:
            if letter in string.ascii_letters:
                emoji_text.append(emoji.emojize(f":regional_indicator_{letter.lower()}:"))
            elif letter == " ":
                emoji_text.append(emoji.emojize(f":blue_square:"))
        return " ".join(emoji_text)

    @commands.command()
    @commands.guild_only()
    @passfail
    async def soundboard(self, ctx):
        "React to the soundboard to play sounds"

        client = self.clients.get(ctx.guild.id)
        if client is None:
            raise Fail("Not connected to voice.")

        message = await ctx.send(self.text_to_emoji("Soundboard"))
        # await message.add_reaction("➡️")

        sound_names = self.redis.smembers(f"soundboard:sounds:{ctx.guild.id}")
        for name in sound_names:
            if name in emoji.UNICODE_EMOJI:
                await message.add_reaction(name)

        def check(reaction, user):
            return user.id != self.bot.user.id

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=120, check=check)
            except asyncio.TimeoutError:
                return NoReact()
            else:
                if self.clients.get(ctx.guild.id) and self.redis.sismember(f"soundboard:sounds:{ctx.guild.id}", reaction.emoji):
                    sound = self.redis.hgetall(f"soundboard:sounds:{ctx.guild.id}:{reaction.emoji}")
                    await self.play_sound(ctx.guild.id, sound["youtube-id"])


def setup(bot):
    bot.add_cog(Soundboard(bot))
