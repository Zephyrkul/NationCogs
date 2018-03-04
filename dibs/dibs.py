import discord
from discord.ext import commands

class Dibs:

    def __init__(self, bot):
        self.bot = bot

    async def on_member_remove(self, member):
        emoji = ("🏡", "🏠", "🏚")[3 * member.server.role_hierarchy.index(member.top_role) // len(member.server.roles)]
        dibs = await self.bot.wait_for_message(check=self.check)
        if not discord.utils.get(dibs.reactions, emoji=emoji, me=True):
            await self.bot.add_reaction(dibs, emoji)

    def check(self, message):
        server = message.server
        channel = message.channel
        if not discord.utils.get(server.roles, name="Dibs Commissioner"):
            return False
        if channel.overwrites_for(server.default_role).send_messages is False:
            return False
        if not channel.permissions_for(server.me).add_reactions:
            return False
        return message.content.lower() == "dibs"

def setup(bot):
    bot.add_cog(Dibs(bot))
