def setup(bot):
    @bot.event
    async def on_ready():
        bot.redis.delete("guild:list")
        bot.redis.sadd("guild:list", *(guild.id for guild in bot.guilds))

        # Cache of guild ID -> name, guild member list, user ID -> name, etc
        for guild in bot.guilds:
            bot.redis.hset(f"guild:{guild.id}", "name", guild.name)

            bot.redis.delete(f"guild:member:{guild.id}")
            bot.redis.sadd(f"guild:member:{guild.id}",
                           *(member.id for member in guild.members))

        for member in bot.get_all_members():
            bot.redis.set(f"user:name:{member.guild.id}:{member.id}", member.display_name)

    @bot.event
    async def on_member_join(member):
        bot.redis.sadd(f"guild:member:{member.guild.id}", member.id)

    @bot.event
    async def on_member_leave(member):
        bot.redis.srem(f"guild:member:{member.guild.id}", member.id)

    @bot.event
    async def on_guild_join(guild):
        bot.redis.sadd("guild:list", guild.id)
        bot.redis.hset(f"guild:{guild.id}", "name", guild.name)

        bot.redis.delete(f"guild:member:{guild.id}")
        bot.redis.sadd(f"guild:member:{guild.id}",
                       *(member.id for member in guild.members))

    @bot.event
    async def on_guild_leave(guild):
        bot.redis.srem("guild:list", guild.id)
        bot.redis.delete(f"guild:{guild.id}")
        bot.redis.delete(f"guild:member:{guild.id}")
