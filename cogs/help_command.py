import discord
from discord.ext import commands

class HelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows help about the bot, a command, or a category'
        })

    def get_command_signature(self, command):
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

            value = "\n".join(self.get_command_signature(command) for command in commands_filtered)
            embed.add_field(name=name, value=value, inline=False)

        await self.context.channel.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(title=f"{cog.qualified_name} | {cog.description}")

        commands = []
        commands_unfiltered = cog.get_commands()
        commands_filtered = await self.filter_commands(commands_unfiltered)
        for command in commands_filtered:
            commands.append(self.get_command_signature(command))

        commands = "\n".join(commands)
        embed.add_field(name="Commands", value=commands, inline=False)

        await self.context.channel.send(embed=embed)

    async def send_command_help(self, command):
        signature = f"{self.clean_prefix}{command.qualified_name} {command.signature or ''}"
        help = command.help or ""

        embed = discord.Embed(title=signature)
        embed.description = help

        if command.cog:
            embed.set_footer(text=command.cog.qualified_name)

        await self.context.channel.send(embed=embed)

def setup(bot):
    bot.help_command = HelpCommand()
