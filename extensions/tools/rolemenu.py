from urllib.parse import urlparse

from discord.ext import commands


from .. import base


class Menu:
    def __init__(self, name="Under Construction",
                 desc="Role menu currently under construction.",
                 mapping={}, channel_id=None, message_id=None):
        self.name = name
        self.desc = desc
        self.mapping = mapping
        self.channel_id = channel_id
        self.message_id = message_id

    @staticmethod
    async def from_redis(redis, channel_id, message_id):
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

        return Menu(name, desc, mapping, channel_id, message_id)

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
            "rolemenu:list", f"{self.channel_id}:{self.message_id}")

    async def delete(self, redis):
        await redis.srem(
            "rolemenu:list", f"{self.channel_id}{self.message_id}")
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

    async def get_menu_from_link(self, ctx, link):
        # Grab the guild, channel, message out of the message link
        # https://discordapp.com/channels/747905649303748678/747921216186220654/748237781519827114
        _, guild_id, channel_id, message_id = \
            urlparse(link).path.lstrip("/").split("/")

        if int(guild_id) != ctx.guild.id:
            raise commands.CommandError(
                "That role menu belongs to a different guild!")

        return await Menu.from_redis(self.redis, channel_id, message_id)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def menu(self, ctx):
        """Create a menu for members to choose their roles
        using message reactions"""

        menu = Menu()
        await menu.post(self.bot, ctx.channel)
        await menu.to_redis(self.redis)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def modifymenu(self, ctx, message_link: str,
                         field: str, *, value: str):
        "Modify the name or description of a role menu"
        menu = await self.get_menu_from_link(ctx, message_link)

        if field == "name":
            menu.name = value
        elif field == "desc":
            menu.desc = value

        await menu.post(self.bot)
        await menu.to_redis(self.redis)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def addrole(self, ctx, message_link: str, emoji: str, *, role: str):
        "Add a role to an existing role menu"

        for irole in ctx.guild.roles:
            if irole.name == role:
                break
        else:
            raise commands.CommandError(f"Role {role} does not exist")

        menu = await self.get_menu_from_link(ctx, message_link)
        menu.mapping[emoji] = irole.id
        await menu.post(self.bot)
        await menu.to_redis(self.redis)

    @commands.command()
    @commands.has_guild_permissions(administrator=True)
    async def remrole(self, ctx, message_link: str, emoji: str):
        "Remove a role from an existing role menu"

        menu = await self.get_menu_from_link(ctx, message_link)
        del menu.mapping[emoji]
        await menu.post(self.bot)
        await menu.to_redis(self.redis)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        if await self.redis.sismember(
                "rolemenu:list", f"{payload.channel_id}:{payload.message_id}"):
            await self.bot.wait_until_ready()
            menu = await Menu.from_redis(
                self.redis, payload.channel_id, payload.message_id)
            await menu.delete(self.redis)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if await self.redis.sismember(
                "rolemenu:list", f"{payload.channel_id}:{payload.message_id}"):
            await self.bot.wait_until_ready()
            menu = await Menu.from_redis(
                self.redis, payload.channel_id, payload.message_id)
            await menu.handle_reaction_add(self.bot, payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if await self.redis.sismember(
                "rolemenu:list", f"{payload.channel_id}:{payload.message_id}"):
            await self.bot.wait_until_ready()
            menu = await Menu.from_redis(
                self.redis, payload.channel_id, payload.message_id)
            await menu.handle_reaction_remove(self.bot, payload)


def setup(bot):
    bot.add_cog(RoleMenu(bot))
