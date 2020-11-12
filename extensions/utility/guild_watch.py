def setup(bot):
    @bot.event
    async def on_ready():
        await bot.redis.delete("guild:list")
        await bot.redis.delete("user:list")

        await bot.redis.sadd("guild:list", *(guild.id for guild in bot.guilds))

        # Cache of guild ID -> name, guild member list, user ID -> name, etc
        for guild in bot.guilds:
            await bot.redis.hset(f"guild:{guild.id}", "name", guild.name)

            await bot.redis.delete(f"guild:member:{guild.id}")
            await bot.redis.sadd(
                f"guild:member:{guild.id}",
                *(member.id for member in guild.members))

            await bot.redis.sadd(
                "user:list", *(member.id for member in guild.members))

        for member in bot.get_all_members():
            await bot.redis.set(
                f"user:name:{member.guild.id}:{member.id}",
                member.display_name)
            await bot.redis.hset(
                f"profile:{member.guild.id}:{member.id}",
                "pfp", str(member.avatar_url))

    @bot.event
    async def on_member_join(member):
        await bot.redis.sadd(f"guild:member:{member.guild.id}", member.id)
        await bot.redis.sadd("user:list", member.id)
        await bot.redis.set(
            f"user:name:{member.guild.id}:{member.id}", member.display_name)
        await bot.redis.hset(
            f"profile:{member.guild.id}:{member.id}",
            "pfp", str(member.avatar_url))

    @bot.event
    async def on_member_leave(member):
        await bot.redis.srem(f"guild:member:{member.guild.id}", member.id)
        await bot.redis.delete(f"user:name:{member.guild.id}:{member.id}")
        await bot.redis.delete(f"profile:{member.guild.id}:{member.id}")

    @bot.event
    async def on_member_update(old, member):
        await bot.redis.set(
            f"user:name:{member.guild.id}:{member.id}", member.display_name)
        await bot.redis.hset(
            f"profile:{member.guild.id}:{member.id}",
            "pfp", str(member.avatar_url))

    @bot.event
    async def on_user_update(old, user):
        # TODO: try and detect username changes?
        pass

    @bot.event
    async def on_guild_join(guild):
        await bot.redis.sadd("guild:list", guild.id)
        await bot.redis.hset(f"guild:{guild.id}", "name", guild.name)

        await bot.redis.delete(f"guild:member:{guild.id}")
        await bot.redis.sadd(f"guild:member:{guild.id}",
                             *(member.id for member in guild.members))

        for member in guild.members:
            await bot.redis.set(
                f"user:name:{member.guild.id}:{member.id}",
                member.display_name)
            await bot.redis.hset(
                f"profile:{member.guild.id}:{member.id}",
                "pfp", str(member.avatar_url))
            await bot.redis.sadd("user:list", member.id)

    @bot.event
    async def on_guild_leave(guild):
        await bot.redis.srem("guild:list", guild.id)
        await bot.redis.delete(f"guild:{guild.id}")
        await bot.redis.delete(f"guild:member:{guild.id}")
