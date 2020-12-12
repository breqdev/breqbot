from discord.ext import commands

from .. import base


class GuildWatch(base.BaseCog):

    category = "Internal"

    @commands.Cog.listener()
    async def on_ready(self):
        await self.redis.delete("guild:list")

        await self.redis.sadd(
            "guild:list", *(guild.id for guild in self.bot.guilds))

        for guild in self.bot.guilds:
            await self.redis.hset(f"guild:{guild.id}", "name", guild.name)

    @commands.Cog.listener()
    async def on_command_completion(self, ctx):
        if ctx.guild is None:
            return

        await self.redis.sadd(f"guild:member:{ctx.guild.id}", ctx.author.id)
        await self.redis.sadd("user:list", ctx.author.id)
        await self.redis.set(
            f"user:name:{ctx.guild.id}:{ctx.author.id}",
            ctx.author.display_name)
        await self.redis.hset(
            f"profile:{ctx.guild.id}:{ctx.author.id}",
            "pfp", str(ctx.author.avatar_url))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.redis.sadd("guild:list", guild.id)
        await self.redis.hset(f"guild:{guild.id}", "name", guild.name)

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        await self.redis.srem("guild:list", guild.id)


def setup(bot):
    bot.add_cog(GuildWatch(bot))
