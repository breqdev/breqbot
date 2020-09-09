import discord
from discord.ext import commands

class HelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            'help': 'Shows help about the bot, a command, or a category'
        })

    def get_command_signature(self, command):
        sig = f"•    {self.clean_prefix}{command.qualified_name} {command.signature}"
        if command.brief:
            sig += f" | {command.brief}"
        elif command.help:
            brief = command.help.split('\n')[0]
            sig += f" | {brief}"

        return sig

    async def send_bot_help(self, mapping):
        embed = discord.Embed(name="Help")
        result = ["Hi, I'm Breqbot! Beep boop :robot:"]
        for cog, commands_unfiltered in mapping.items():
            commands_filtered = await self.filter_commands(commands_unfiltered)
            if len(commands_filtered) == 0:
                continue
            result.append("---")
            if cog:
                result.append(f"{cog.qualified_name}")
            else:
                result.append("General:")
            for command in commands_filtered:
                result.append(self.get_command_signature(command))
        embed.description = "\n".join(result)
        await self.context.channel.send(embed=embed)

    async def send_cog_help(self, cog):
        embed = discord.Embed(name="Help")
        result = ["Hi, I'm Breqbot! Beep boop :robot:",
                  "---",
                  cog.qualified_name]
        commands_unfiltered = cog.get_commands()
        commands_filtered = await self.filter_commands(commands_unfiltered)
        for command in commands_filtered:
            result.append(self.get_command_signature(command))
        embed.description = "\n".join(result)
        await self.context.channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(name="Help")
        result = ["Hi, I'm Breqbot! Beep boop :robot:",
                  "---"]
        result.append(f"{self.clean_prefix}{command.qualified_name}")
        result.append(command.help or "")
        embed.description = "\n".join(result)
        await self.context.channel.send(embed=embed)
