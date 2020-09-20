import re
import urllib.parse

import discord
from discord.ext import commands

import youtube_dl

from .breqcog import Breqcog, passfail, Fail

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
        print(id)
        if not bool(re.match(r"[A-Za-z0-9\-_]{11}", id)):
            raise Fail(f"Invalid video ID: {id}")

        return id

    def get_yt_title(self, id):
        try:
            with youtube_dl.YoutubeDL({"simulate": True}) as ydl:
                metadata = ydl.extract_info(id)
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

    @commands.command()
    @commands.guild_only()
    @passfail
    async def playsound(self, ctx, emoji: str):
        "Play a sound"
        return "Coming soon!"

    @commands.command()
    @commands.guild_only()
    @passfail
    async def soundboard(self, ctx):
        "React to the soundboard to play sounds"
        return "Coming soon!"

def setup(bot):
    bot.add_cog(Soundboard(bot))
