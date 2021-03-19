from discord.ext import commands

from bot import base


class Pronouns(base.BaseCog):
    "Tell people your pronouns!"

    category = "Profile"

    @commands.group(invoke_without_command=True)
    async def pronouns(self, ctx, *, member: base.FuzzyMember):
        "Get another member's pronouns! No need to ping them :)"
        pronouns = await self.redis.get(
            f"pronouns:{ctx.guild.id}:{member.id}")

        if pronouns:
            await ctx.send(f"{member.display_name}'s pronouns are {pronouns}!")
        else:
            await ctx.send(
                f"{member.display_name} has not set "
                f"{member.display_name}'s pronouns yet. "
                f"(The command is `{self.bot.main_prefix}setpronouns`!)")

    @pronouns.command()
    async def set(self, ctx, *, pronouns: str):
        "Set your pronouns!"
        await self.redis.set(
            f"pronouns:{ctx.guild.id}:{ctx.author.id}", pronouns)
        await ctx.message.add_reaction("✅")


def setup(bot):
    bot.add_cog(Pronouns(bot))
