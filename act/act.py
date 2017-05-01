import inflect
import discord
from discord.ext import commands


class Act:
    def __init__(self, bot):
        self.bot = bot
        self.engine = inflect.engine()

    @commands.command(pass_context=True)
    async def act(self, ctx, *, user: discord.Member=None):
        """If a command isn't found, this command is called instead!"""
        user = user if user else ctx.message.author
        action = ctx.invoked_with
        if not self.engine.singular_noun(action):
            action = self.engine.plural(action)
        await self.bot.send_message(ctx.message.channel,
                                    "*{} {}*".format(action, user.mention))

    async def on_command_error(self, error, ctx):
        """haxx"""
        if not isinstance(error, commands.CommandNotFound) and \
                not isinstance(error, commands.CheckFailure):
            return
        pre = ctx.prefix + ctx.invoked_with
        user = ctx.message.content[len(pre):].strip()
        if user:
            try:
                user = commands.MemberConverter(ctx, user).convert()
            except commands.BadArgument:
                return
        await ctx.invoke(self.act, user=user)


def setup(bot):
    bot.add_cog(Act(bot))
