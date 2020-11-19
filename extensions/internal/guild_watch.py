from discord.ext import commands

from .. import base


class GuildWatch(base.BaseCog):
    @commands.Cog.listener()
    async def on_ready(self):
        await self.redis.delete("guild:list")
        await self.redis.delete("user:list")

        await self.redis.sadd(
            "guild:list", *(guild.id for guild in self.bot.guilds))

        # Cache of guild ID -> name, guild member list, user ID -> name, etc
        for guild in self.bot.guilds:
            await self.redis.hset(f"guild:{guild.id}", "name", guild.name)

            await self.redis.delete(f"guild:member:{guild.id}")
            await self.redis.sadd(
                f"guild:member:{guild.id}",
                *(member.id for member in guild.members))

            await self.redis.sadd(
                "user:list", *(member.id for member in guild.members))

        for member in self.bot.get_all_members():
            await self.redis.set(
                f"user:name:{member.guild.id}:{member.id}",
                member.display_name)
            await self.redis.hset(
                f"profile:{member.guild.id}:{member.id}",
                "pfp", str(member.avatar_url))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        await self.redis.sadd(f"guild:member:{member.guild.id}", member.id)
        await self.redis.sadd("user:list", member.id)
        await self.redis.set(
            f"user:name:{member.guild.id}:{member.id}", member.display_name)
        await self.redis.hset(
            f"profile:{member.guild.id}:{member.id}",
            "pfp", str(member.avatar_url))

    @commands.Cog.listener()
    async def on_member_leave(self, member):
        await self.redis.srem(f"guild:member:{member.guild.id}", member.id)
        await self.redis.delete(f"user:name:{member.guild.id}:{member.id}")
        await self.redis.delete(f"profile:{member.guild.id}:{member.id}")

    @commands.Cog.listener()
    async def on_member_update(self, old, member):
        await self.redis.set(
            f"user:name:{member.guild.id}:{member.id}", member.display_name)
        await self.redis.hset(
            f"profile:{member.guild.id}:{member.id}",
            "pfp", str(member.avatar_url))

    @commands.Cog.listener()
    async def on_user_update(self, old, user):
        # TODO: try and detect username changes?
        pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await self.redis.sadd("guild:list", guild.id)
        await self.redis.hset(f"guild:{guild.id}", "name", guild.name)

        await self.redis.delete(f"guild:member:{guild.id}")
        await self.redis.sadd(f"guild:member:{guild.id}",
                              *(member.id for member in guild.members))

        for member in guild.members:
            await self.redis.set(
                f"user:name:{member.guild.id}:{member.id}",
                member.display_name)
            await self.redis.hset(
                f"profile:{member.guild.id}:{member.id}",
                "pfp", str(member.avatar_url))
            await self.redis.sadd("user:list", member.id)

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        await self.redis.srem("guild:list", guild.id)
        await self.redis.delete(f"guild:{guild.id}")
        await self.redis.delete(f"guild:member:{guild.id}")


def setup(bot):
    bot.add_cog(GuildWatch(bot))
