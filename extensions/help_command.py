import os
import uuid

import discord
from discord.ext import commands


class HelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows help about the bot, a command, or a category'
        })

    def get_command_description(self, command):
        sig = f"• `{self.clean_prefix}{command.qualified_name}"
        if command.signature:
            sig += f" {command.signature}` "
        else:
            sig += "`"
        if command.brief:
            sig += f" | {command.brief}"
        elif command.help:
            brief = command.help.split('\n')[0]
            sig += f" | {brief}"

        return sig

    def get_command_signature(self, command):
        sig = f"{self.clean_prefix}{command.qualified_name}"
        if command.signature:
            sig += f" {command.signature}"
        return sig

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Hi, I'm Breqbot! Beep boop :robot:")

        for cog, commands_unfiltered in mapping.items():
            commands_filtered = await self.filter_commands(commands_unfiltered)
            if len(commands_filtered) == 0:
                continue

            if cog:
                name = f"**{cog.qualified_name}:**"
            else:
                name = "**General:**"

            value = " ".join(f"`{self.get_command_signature(command)}`"
                             for command in commands_filtered)
            embed.add_field(name=name, value=value, inline=False)

        await self.context.channel.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed()
        embed.title = f"{cog.qualified_name} | {cog.description}"

        commands = []
        commands_unfiltered = cog.get_commands()
        commands_filtered = await self.filter_commands(commands_unfiltered)
        for command in commands_filtered:
            commands.append(self.get_command_description(command))

        commands = "\n".join(commands)
        embed.add_field(name="Commands", value=commands, inline=False)

        await self.context.channel.send(embed=embed)

    async def send_command_help(self, command):
        signature = self.get_command_signature(command)
        help = command.help or ""

        embed = discord.Embed(title=signature)
        embed.description = help

        if command.cog:
            embed.set_footer(text=command.cog.qualified_name)

        await self.context.channel.send(embed=embed)


def setup(bot):
    @bot.event
    async def on_command_error(ctx, exception):
        if (isinstance(exception, commands.CheckFailure)
                or isinstance(exception, commands.DisabledCommand)):
            await ctx.message.add_reaction("⛔")

        elif isinstance(exception, commands.UserInputError):
            embed = discord.Embed()
            embed.title = "Usage:"
            if ctx.command.signature:
                embed.description = (f"`{bot.command_prefix}{ctx.command.name}"
                                     f" {ctx.command.signature}`")
            else:
                embed.description = f"`{bot.command_prefix}{ctx.command.name}`"
            embed.set_footer(
                text=ctx.command.brief or ctx.command.help.split("\n")[0])
            await ctx.send(embed=embed)

        elif isinstance(exception, commands.CommandNotFound):
            # await ctx.message.add_reaction("🤔")
            pass
        else:
            error_id = str(uuid.uuid4())

            embed = discord.Embed(title="Aw, snap!")
            embed.description = ("Something went wrong while running this "
                                 "command. If this continues, "
                                 f"[report this]({os.getenv('BUG_REPORT')}) "
                                 "to Breq.")

            embed.add_field(name="Error ID", value=error_id)

            await ctx.send(embed=embed)
            await ctx.message.add_reaction("⚠️")

            print("="*20)
            print(f"Exception raised with error ID {error_id}")
            raise exception

    bot.help_command = HelpCommand()
