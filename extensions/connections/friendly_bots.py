import discord
from discord.ext import commands

from .. import base


class FriendlyBots(base.BaseCog):
    "Breqbot can talk to other friendly bots!"

    category = "Connections"

    @staticmethod
    def pack_whisper(message):
        return " ".join(format(ord(char), "b").zfill(8) for char in message)

    @staticmethod
    def unpack_whisper(whisper):
        whisper = whisper.replace(" ", "")
        return int(whisper, 2).to_bytes(len(whisper) // 8, 'big').decode()

    @commands.command(hidden=True)
    async def whisper(self, ctx, *, whisper: str):
        if not ctx.author.bot:
            raise commands.CommandError("Only bots can whisper to Breqbot!")

        message = self.unpack_whisper(whisper)

        await ctx.message.add_reaction("✅")

        await ctx.send(f"{ctx.author.mention} says **{message}**")

    @commands.command()
    async def tell(self, ctx, bot: discord.User, *, message: str):
        "Send a message to one of Breqbot's friends!"

        if not bot.bot:
            raise commands.CommandError(
                "Breqbot can only whisper to other bots!")

        if not (await self.redis.sismember("user:friend:list", bot.id)):
            raise commands.CommandError(
                "Breqbot can only whisper with friends! "
                "(want your bot to make friends with Breqbot? "
                "shoot Breq a DM, she'll help you add your bot!)")

        whisper = self.pack_whisper(message)

        prefix = await self.redis.hget(f"user:friend:{bot.id}", "prefix")

        await ctx.send(f"{prefix} {whisper}")


def setup(bot):
    bot.add_cog(FriendlyBots(bot))

    @bot.event
    async def on_message(message):
        ctx = await bot.get_context(message)

        if message.author.bot:
            is_friendly = await bot.redis.sismember(
                "user:friend:list", message.author.id)
            if not is_friendly:
                return

            if ctx.command is not None and ctx.command.name != "whisper":
                return

        await bot.invoke(ctx)
