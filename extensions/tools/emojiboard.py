import discord
from discord.ext import commands

from .. import base


class EmojiBoard(base.BaseCog):
    "Like starboards, but for any emoji."

    category = "Tools"

    def cog_check(self, ctx):
        return ctx.author.guild_permissions.manage_messages

    @commands.group(invoke_without_command=True)
    async def emojiboard(self, ctx,
                         emoji: str,
                         amount: int = 1):
        """Create an EmojiBoard with the specific emoji!
        Set amount = 0 to remove."""

        identifier = f"{ctx.channel.id}:{emoji}"

        if amount > 0:
            # Create a new emojiboard (or modify the amount)
            await self.redis.sadd(
                f"emojiboard:list:{ctx.guild.id}", identifier)
            await self.redis.hmset_dict(
                f"emojiboard:board:{identifier}", amount=amount)

        else:
            # Delete an existing emojiboard
            await self.redis.srem(
                f"emojiboard:list:{ctx.guild.id}", identifier)
            await self.redis.delete(f"emojiboard:board:{identifier}")

        await ctx.message.add_reaction("✅")

    @emojiboard.command()
    async def list(self, ctx):
        "List the EmojiBoards enabled in this server"

        embed = discord.Embed(title=f"EmojiBoards on {ctx.guild.name}")

        board_names = []

        for identifier in (await self.redis.smembers(
                f"emojiboard:list:{ctx.guild.id}")):
            channel_id, emoji = identifier.split(":", 1)
            needed_amount = int(await self.redis.hget(
                f"emojiboard:board:{identifier}", "amount"))
            channel = self.bot.get_channel(int(channel_id))

            board_names.append(
                f"**≥{needed_amount}** × {emoji} → {channel.mention}")

        embed.description = "\n".join(board_names)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if not payload.guild_id:
            return

        channel = self.bot.get_channel(payload.channel_id)

        for identifier in (await self.redis.smembers(
                f"emojiboard:list:{channel.guild.id}")):
            channel_id, emoji = identifier.split(":", 1)

            if emoji == str(payload.emoji):
                await self.handle_board(
                    identifier, channel, payload.message_id)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if not payload.guild_id:
            return

        channel = self.bot.get_channel(payload.channel_id)

        for identifier in (await self.redis.smembers(
                f"emojiboard:list:{channel.guild.id}")):
            channel_id, emoji = identifier.split(":", 1)

            if emoji == str(payload.emoji):
                await self.handle_board(
                    identifier, channel, payload.message_id)

    async def make_response(self, message, emoji, amount):
        "Create a packed Response about a message for posting on a board"

        content = f"{emoji} **{amount}** {message.channel.mention}"

        embed = discord.Embed()
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.avatar_url)

        embed.description = message.content
        embed.timestamp = message.edited_at or message.created_at

        if message.attachments:
            embed.set_image(url=message.attachments[0].proxy_url)

        return base.Response(content=content, embed=embed)

    async def handle_board(self, identifier, channel, message_id):
        message = await channel.fetch_message(message_id)

        board_message = await self.redis.get(
            f"emojiboard:board:{identifier}:{message.id}")

        channel_id, emoji = identifier.split(":", 1)
        board_channel = self.bot.get_channel(int(channel_id))

        for reaction in message.reactions:
            if str(reaction.emoji) == emoji:
                amount = reaction.count
                break
        else:
            amount = 0

        response = await self.make_response(message, emoji, amount)

        if board_message is None:
            # Message got an applicable reaction, but isn't on the board yet.

            needed_amount = int(await self.redis.hget(
                f"emojiboard:board:{identifier}", "amount"))

            if amount >= needed_amount:
                # Message has enough reactions, let's add it to the board!
                board_message = await response.send_to(board_channel)

                await self.redis.set(
                    f"emojiboard:board:{identifier}:{message.id}",
                    board_message.id)

        else:
            try:
                # Message is already on the board, update the count.
                message = await board_channel.fetch_message(int(board_message))
            except discord.NotFound:
                # Message has been removed from the board by a server admin
                return
            else:
                await response.send_to(message)


def setup(bot):
    bot.add_cog(EmojiBoard(bot))
