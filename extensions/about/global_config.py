import typing

import discord
from discord.ext import commands

from .. import base


class GlobalConfig(base.BaseCog):
    "Enable and disable Breqbot functions globally"

    category = "About"

    def cog_check(self, ctx):
        return base.config_only(ctx)

    @commands.command()
    async def guilds(self, ctx):
        "List guilds that the bot is in"

        embed = discord.Embed(title="Breqbot is in...")

        guilds = []
        for guild_id in await self.redis.smembers("guild:list"):
            guilds.append((await self.redis.hget(f"guild:{guild_id}", "name"),
                          await self.redis.scard(f"guild:member:{guild_id}")))

        embed.description = "\n".join(f"{name}: {size}"
                                      for name, size in guilds)
        await ctx.send(embed=embed)

    @commands.command()
    async def activity(self, ctx, type: str, *, desc: str):
        "Change Breqbot's status in Discord"

        await self.redis.set("activity:type", type)
        await self.redis.set("activity:name", desc)
        await self.load_activity()

    async def load_activity(self):
        type = await self.redis.get("activity:type") or "watching"
        desc = await self.redis.get("activity:name") or ";help | bot.breq.dev"

        if type.lower().strip() == "playing":
            activity = discord.Game(desc)
        elif type.lower().strip() == "watching":
            activity = discord.Activity(
                name=desc, type=discord.ActivityType.watching)
        elif type.lower().strip() == "streaming":
            activity = discord.Streaming(url="https://bot.breq.dev/")
        elif type.lower().strip() == "listening":
            activity = discord.Activity(
                name=desc, type=discord.ActivityType.listening)
        elif type.lower().strip() == "competing":
            activity = discord.Activity(
                name=desc, type=discord.ActivityType.competing)

        await self.bot.change_presence(status=discord.Status.online,
                                       activity=activity)

    @commands.command()
    async def addfriend(self, ctx, bot_id: int,
                        prefix: typing.Optional[str] = None):
        "Add a friendly bot to Breqbot's list of friends!"

        if prefix is None:
            prefix = f"<@{bot_id}>"

        await self.redis.hmset_dict(
            f"user:friend:{bot_id}", {"prefix": prefix})

        await self.redis.sadd("user:friend:list", bot_id)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def remfriend(self, ctx, bot_id: int):
        "Remove a friendly bot from Breqbot's list of friends"

        await self.redis.srem("user:friend:list", bot_id)
        await self.redis.delete(f"user:friend:{bot_id}")
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def friends(self, ctx):
        "List Breqbot's friends!"

        friends = await self.redis.smembers("user:friend:list")
        await ctx.send(" ".join(f"<@{id}>" for id in friends))

    @commands.command()
    async def addalsotry(self, ctx, bot: discord.User, invite: str,
                         *, desc: str):
        "Add a bot to Breqbot's 'also try <name>!' feature!"

        await self.redis.hset(f"alsotry:{bot.id}", "invite", invite)
        await self.redis.hset(f"alsotry:{bot.id}", "name", bot.name)
        await self.redis.hset(f"alsotry:{bot.id}", "desc", desc)

        await self.redis.sadd("alsotry:list", bot.id)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def remalsotry(self, ctx, bot_id: int):
        "Remove a bot from the 'also try' list."

        await self.redis.srem("alsotry:list", bot_id)
        await self.redis.delete(f"alsotry:{bot_id}")
        await ctx.message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_activity()


def setup(bot):
    bot.add_cog(GlobalConfig(bot))
