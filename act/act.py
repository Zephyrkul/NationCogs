from copy import copy
import inflect
import discord
from discord.ext import commands


class Act:
    def __init__(self, bot):
        self.bot = bot
        self.engine = inflect.engine()

    @commands.command(pass_context=True)
    async def act(self, ctx, *, user: discord.Member=None):
        """Acts on the specified user.

        Modifying this command (e.g. through permissions) will affect
        all "fake" commands enabled through this cog."""
        user = user if user else ctx.message.author
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
        act = copy(self.act)
        # proper event dispatching
        self.bot.dispatch("command", act, ctx)
        try:
            await act.invoke(ctx)
        except commands.CommandError as e:
            if isinstance(e, commands.MissingRequiredArgument) or \
                    isinstance(e, commands.BadArgument):
                # hack help text
                singular = self.engine.singular_noun(ctx.invoked_with)
                act.name = ctx.invoked_with
                act.help = (ctx.invoked_with if singular else
                            self.engine.plural_noun(
                                ctx.invoked_with)).title() + self.act.help[7:27]
            act.dispatch_error(e, ctx)
        else:
            self.bot.dispatch('command_completion', act, ctx)


def setup(bot):
    bot.add_cog(Act(bot))
