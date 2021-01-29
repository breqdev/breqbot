from discord.ext import commands

from .. import base


class Config(base.BaseCog):
    "Enable and disable Breqbot's features"

    category = "About"

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def enable(self, ctx, feature: str):
        "Enable a Breqbot feature in this guild."
        if feature == "website":
            await self.redis.hset(f"guild:{ctx.guild.id}", "website", "1")
        elif feature == "nsfw":
            await self.redis.set(
                f"channel:{ctx.guild.id}:{ctx.channel.id}:nsfw", "1")
        else:
            raise commands.CommandError(f"Unsupported feature: {feature}")

        await ctx.message.add_reaction("✅")

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def disable(self, ctx, feature: str):
        "Disable a Breqbot feature in this guild."
        if feature == "website":
            await self.redis.hset(f"guild:{ctx.guild.id}", "website", "0")
        elif feature == "nsfw":
            await self.redis.set(
                f"channel:{ctx.guild.id}:{ctx.channel.id}:nsfw", "0")
        else:
            raise commands.CommandError(f"Unsupported feature: {feature}")

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Config(bot))
