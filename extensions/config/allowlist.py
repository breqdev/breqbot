from discord.ext import commands

from ..base import BaseCog


class AllowList(BaseCog):
    "Enable and disable Breqbot functions"

    # TODO: support enabling and disabling individual cogs?

    @commands.command()
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def enwebsite(self, ctx, state: int):
        """Enable or disable the bot's website for this guild and its members
        :mobile_phone_off:"""

        self.redis.hset(f"guild:{ctx.guild.id}", "website", state)

        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(AllowList(bot))
