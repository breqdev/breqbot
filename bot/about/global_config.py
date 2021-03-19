import typing

import discord
from discord.ext import commands

from bot import base


class GlobalConfig(base.BaseCog):
    "Enable and disable Breqbot functions globally"

    category = "About"

    def cog_check(self, ctx):
        return base.config_only(ctx)

    # Diagnostic Commands

    @commands.command()
    async def guilds(self, ctx):
        "List guilds that the bot is in"

        embed = discord.Embed(title="Breqbot is in...")

        guilds = []
        for guild_id in await self.redis.smembers("guild:list"):
            guilds.append((
                guild_id,
                await self.redis.hget(f"guild:{guild_id}", "name"),
                await self.redis.scard(f"guild:member:{guild_id}")
            ))

        embed.description = "\n".join(f"{name}: {size} *({id})*"
                                      for id, name, size in guilds)
        await ctx.send(embed=embed)

    # Set Bot Presence

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

    # Manage Bot Friends List

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

    # Manage User Bans

    @commands.command()
    async def ban(self, ctx, user_id: int):
        "Ban a user from using Breqbot"
        await self.redis.sadd("user:banned:list", user_id)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def unban(self, ctx, user_id: int):
        "Revert a user ban"
        await self.redis.srem("user:banned:list", user_id)
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def guildban(self, ctx, guild_id: int):
        "Leave a guild and prevent re-joining"
        await self.redis.sadd("guild:banned:list", guild_id)

        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()

    @commands.command()
    async def guildunban(self, ctx, guild_id: int):
        "Revert a guild ban"
        await self.redis.srem("guild:banned:list", guild_id)

    # Manage Guild Lock

    @commands.command()
    async def guildlock(self, ctx, enable: bool):
        "Enable or disable the lock preventing Breqbot from joining new guilds"
        await self.redis.set("guildlock:enabled", int(enable))
        await ctx.message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_activity()

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if int(await self.redis.get("guildlock:enabled")):
            await guild.leave()

        if int(await self.redis.sismember("guild:banned:list", guild.id)):
            await guild.leave()


def setup(bot):
    bot.add_cog(GlobalConfig(bot))

    @bot.check
    async def check_banned(ctx):
        return not int(
            await bot.redis.sismember("user:banned:list", ctx.author.id))
