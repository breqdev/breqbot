import discord
from discord.ext import commands


from .. import base


class Menu:
    def __init__(self, name="Under Construction",
                 desc="Role menu currently under construction.",
                 mapping={}, guild_id=None, channel_id=None, message_id=None):
        self.name = name
        self.desc = desc
        self.mapping = mapping
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id

    @staticmethod
    async def from_redis(redis, guild_id, channel_id, message_id):
        hash = await redis.hgetall(f"rolemenu:{channel_id}:{message_id}")
        if not hash:
            raise commands.CommandError(
                f"Role Menu with ID {channel_id}:{message_id} does not exist")

        name = hash["name"]
        desc = hash["desc"]

        mapping = {}
        for key, val in hash.items():
            if key.startswith("emoji:"):
                emoji = key[len("emoji:"):]
                mapping[emoji] = val

        return Menu(name, desc, mapping, guild_id, channel_id, message_id)

    async def to_redis(self, redis):
        hash = {
            "name": self.name,
            "desc": self.desc,
            "message_id": self.message_id,
            "channel_id": self.channel_id
        }

        for key, val in self.mapping.items():
            hash[f"emoji:{key}"] = val

        await redis.hmset_dict(
            f"rolemenu:{self.channel_id}:{self.message_id}", hash)
        await redis.sadd(
            f"rolemenu:list:{self.guild_id}",
            f"{self.channel_id}:{self.message_id}")

    async def delete(self, redis):
        await redis.srem(
            f"rolemenu:list:{self.guild_id}",
            f"{self.channel_id}:{self.message_id}")
        await redis.delete(f"rolemenu:{self.channel_id}:{self.message_id}")

    async def post(self, bot, channel=None):
        text = []

        text.append(f"Role Menu: **{self.name}**")
        text.append(self.desc)
        text.append("")

        if self.message_id:
            guild = bot.get_channel(int(self.channel_id)).guild
        elif channel:
            guild = channel.guild

        for key, val in self.mapping.items():
            text.append(f"{key}: {guild.get_role(int(val))}")

        text = "\n".join(text)

        if self.message_id:
            message = await (bot.get_channel(int(self.channel_id))
                             .fetch_message(int(self.message_id)))
            await message.edit(content=text)

        elif channel:
            message = await channel.send(text)
            self.channel_id = channel.id
            self.message_id = message.id

        # Remove unused reactions
        for reaction in message.reactions:
            if reaction.emoji in self.mapping:
                continue
            await message.clear_reaction(reaction.emoji)

        # Add new reactions
        for emoji in self.mapping:
            for reaction in message.reactions:
                if reaction.emoji == emoji:
                    break
            else:
                # Emoji not found in reactions
                await message.add_reaction(emoji)

    def get_reaction_context(self, bot, payload):
        if payload.user_id == bot.user.id:
            return False, None, None

        emoji = payload.emoji
        if emoji.is_custom_emoji():
            return False, None, None

        role_id = self.mapping.get(payload.emoji.name)
        if not role_id:
            return False, None, None

        role = bot.get_channel(payload.channel_id).guild.get_role(int(role_id))

        if payload.member:
            member = payload.member
        else:
            member = (bot.get_channel(payload.channel_id).guild
                      .get_member(payload.user_id))
            if not member:
                return False, None, None

        return True, role, member

    async def handle_reaction_add(self, bot, payload):
        valid, role, member = self.get_reaction_context(bot, payload)
        if not valid:
            return

        for irole in member.roles:
            if irole.id == role.id:
                return

        roles = member.roles
        roles.append(role)
        await member.edit(roles=roles)

    async def handle_reaction_remove(self, bot, payload):
        valid, role, member = self.get_reaction_context(bot, payload)
        if not valid:
            return

        for irole in member.roles:
            if role.id == role.id:
                break  # Role exists
        else:
            return  # Role does not exist, cannot be removed

        roles = member.roles
        roles.remove(role)
        await member.edit(roles=roles)


class RoleMenu(base.BaseCog):
    "Create and manage menus for users to choose their roles"

    category = "Tools"

    def cog_check(self, ctx):
        return ctx.author.guild_permissions.administrator

    async def get_menu(self, message):
        return await Menu.from_redis(
            self.redis, message.guild.id, message.channel.id, message.id)

    @commands.group(invoke_without_command=True)
    async def menu(self, ctx):
        pass

    @menu.command()
    async def create(self, ctx):
        """Create a menu for members to choose their roles
        using message reactions"""

        menu = Menu(guild_id=ctx.guild.id)
        await menu.post(self.bot, ctx.channel)
        await menu.to_redis(self.redis)

    @menu.command()
    async def set(self, ctx, message: discord.Message,
                  field: str, *, value: str):
        "Modify the name or description of a role menu"
        menu = await self.get_menu(message)

        if field == "name":
            menu.name = value
        elif field == "desc":
            menu.desc = value

        await menu.post(self.bot)
        await menu.to_redis(self.redis)

    @menu.command()
    async def add(self, ctx, message: discord.Message,
                  emoji: str, *, role: discord.Role):
        "Add a role to an existing role menu"

        menu = await self.get_menu(message)
        menu.mapping[emoji] = role.id
        await menu.post(self.bot)
        await menu.to_redis(self.redis)

    @menu.command()
    async def remove(self, ctx, message: discord.Message, emoji: str):
        "Remove a role from an existing role menu"

        menu = await self.get_menu(message)
        del menu.mapping[emoji]
        await menu.post(self.bot)
        await menu.to_redis(self.redis)

    @menu.command()
    async def list(self, ctx):
        "List active RoleMenus"

        embed = discord.Embed(title=f"RoleMenus on {ctx.guild.name}")

        rolemenus = []

        for identifier in (await self.redis.smembers(
                f"rolemenu:list:{ctx.guild.id}")):
            channel_id, message_id = identifier.split(":", 1)
            channel = self.bot.get_channel(int(channel_id))
            message = await channel.fetch_message(int(message_id))

            menu = await Menu.from_redis(
                self.redis, ctx.guild.id, channel_id, message_id)

            rolemenus.append(
                f"[{menu.name}]({message.jump_url}): {menu.desc}")

        embed.description = "\n".join(rolemenus)

        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if await self.redis.sismember(
                f"rolemenu:list:{payload.guild_id}",
                f"{payload.channel_id}:{payload.message_id}"):
            await self.bot.wait_until_ready()
            menu = await Menu.from_redis(
                self.redis, payload.guild_id,
                payload.channel_id, payload.message_id)
            await menu.delete(self.redis)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if await self.redis.sismember(
                f"rolemenu:list:{payload.guild_id}",
                f"{payload.channel_id}:{payload.message_id}"):
            await self.bot.wait_until_ready()
            menu = await Menu.from_redis(
                self.redis, payload.guild_id,
                payload.channel_id, payload.message_id)
            await menu.handle_reaction_add(self.bot, payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if await self.redis.sismember(
                f"rolemenu:list:{payload.guild_id}",
                f"{payload.channel_id}:{payload.message_id}"):
            await self.bot.wait_until_ready()
            menu = await Menu.from_redis(
                self.redis, payload.guild_id,
                payload.channel_id, payload.message_id)
            await menu.handle_reaction_remove(self.bot, payload)


def setup(bot):
    bot.add_cog(RoleMenu(bot))
