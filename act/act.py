from copy import copy
import inflect
import discord
from discord.ext import commands


class Act:
    def __init__(self, bot):
        self.bot = bot
        self.engine = inflect.engine()

    @commands.command(pass_context=True)
    async def act(self, ctx, *, user: discord.Member):
        """Acts on the specified user.

        Modifying this command (e.g. through permissions) will affect
        all "fake" commands enabled through this cog."""
        action = ctx.invoked_with
        if not self.engine.singular_noun(action):
            action = self.engine.plural_noun(action)
        await self.bot.send_message(ctx.message.channel,
                                    "*{} {}*".format(action, user.mention))

    async def on_command_error(self, error, ctx):
        """haxx"""
        if not isinstance(error, commands.CommandNotFound) and \
                (not isinstance(error, commands.CheckFailure) or
                 ctx.command.callback == self.act.callback):
            return
        if not ctx.invoked_with.isalpha():
            return
        act = copy(self.act)
        # proper event dispatching
        self.bot.dispatch("command", act, ctx)
        try:
            await act.invoke(ctx)
        except commands.CommandError as e:
            if isinstance(e, commands.MissingRequiredArgument) or \
                    isinstance(e, commands.BadArgument):
                # prevent help text
                return
            act.dispatch_error(e, ctx)
        else:
            self.bot.dispatch('command_completion', act, ctx)


def setup(bot):
    bot.add_cog(Act(bot))
