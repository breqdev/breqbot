import discord
from discord.ext import commands

from ..base import BaseCog, UserError


class Config(BaseCog):
    "Enable and disable Breqbot functions"

    @commands.command()
    @commands.check(BaseCog.config_only)
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
    @commands.check(BaseCog.config_only)
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
    @commands.check(BaseCog.config_only)
    async def addfriend(self, ctx, bot_id: int):
        "Add a friendly bot to Breqbot's list of friends!"

        await self.redis.sadd("user:friend:list", bot_id)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(BaseCog.config_only)
    async def remfriend(self, ctx, bot_id: int):
        "Remove a friendly bot from Breqbot's list of friends"

        await self.redis.srem("user:friend:list", bot_id)
        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.check(BaseCog.config_only)
    async def friends(self, ctx):
        "List Breqbot's friends!"

        friends = await self.redis.smembers("user:friend:list")
        await ctx.send(" ".join(f"<@!{id}>" for id in friends))

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def enable(self, ctx, feature: str):
        "Enable a Breqbot feature in this guild."
        if feature == "website":
            await self.redis.hset(f"guild:{ctx.guild.id}", "website", "1")
        else:
            raise UserError(f"Unsupported feature: {feature}")

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def disable(self, ctx, feature: str):
        "Disable a Breqbot feature in this guild."
        if feature == "website":
            await self.redis.hset(f"guild:{ctx.guild.id}", "website", "0")
        else:
            raise UserError(f"Unsupported feature: {feature}")

        await ctx.message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_activity()


def setup(bot):
    bot.add_cog(Config(bot))
