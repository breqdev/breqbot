def setup(bot):
    @bot.event
    async def on_message(message):
        if message.author.bot:
            is_friendly = await bot.redis.sismember(
                "user:friend:list", message.author.id)
            if not is_friendly:
                return

        ctx = await bot.get_context(message)
        await bot.invoke(ctx)
