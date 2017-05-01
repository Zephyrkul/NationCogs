import os
from copy import deepcopy
from random import choice

import discord
from discord.ext import commands

from cogs.utils.chat_formatting import pagify
from .utils.dataIO import dataIO
from __main__ import send_cmd_help


class Theme:
    def __init__(self, bot):
        self.bot = bot
        self._themes = dataIO.load_json("data/themes/themes.json")

    @commands.command(pass_context=True, no_pm=True)
    async def theme(self, ctx, *, user: discord.Member=None):
        """Plays one of your themes, or one of the specified user's."""
        if self.bot.get_cog("Audio") is None:
            return await self.bot.say("This cog requires the Audio cog.")
        user = user if user else ctx.message.author
        if user != self.bot.user and (user.id not in self._themes or
                                      not self._themes[user.id]):
            return await self.bot.say("{} has no themes set.".format(
                user.display_name))
        if user == self.bot.user:
            await ctx.invoke(self.bot.get_command("sing"))
        else:
            await ctx.invoke(self.bot.get_command("play"),
                             url_or_search_terms=choice(self._themes[user.id]))

    @commands.group(pass_context=True)
    async def themes(self, ctx):
        """Configure your themes."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            try:
                message = "Your themes:\n\t{}".format("\n\t".join(
                    self._themes[ctx.message.author.id]))
            except KeyError:
                return
            if len(message) > 1000:
                for page in pagify(message):
                    await self.bot.whisper("```{}```".format(page.strip()))
            else:
                await self.bot.say("```{}```".format(message))

    @themes.command(name="add", pass_context=True)
    async def _themes_add(self, ctx, *, theme):
        """Adds the specified theme to your themes."""
        theme = theme.strip("<>")
        audio = self.bot.get_cog("Audio")
        if audio is None:
            return await self.bot.say("This cog requires the Audio cog.")
        if audio._match_any_url(theme) and \
                not audio._valid_playable_url(theme):
            return await self.bot.say("That's not a valid URL.")
        self._themes.setdefault(ctx.message.author.id, []).append(theme)
        dataIO.save_json("data/themes/themes.json", self._themes)
        await self.bot.say("Theme added.")

    @themes.command(name="remove", pass_context=True)
    async def _themes_remove(self, ctx, *, theme):
        """Removes the specified theme from your themes."""
        theme = theme.strip("<>")
        try:
            self._themes[ctx.message.author.id].remove(theme)
        except KeyError:
            await self.bot.say("You don't have any themes set.")
        except ValueError:
            await self.bot.say("That theme isn't in your list of themes")
        else:
            dataIO.save_json("data/themes/themes.json", self._themes)
            await self.bot.say("Theme removed.")

    @themes.command(name="clear", pass_context=True)
    async def _themes_clear(self, ctx):
        """Removes all of your set themes."""
        try:
            del self._themes[ctx.message.author.id]
        except KeyError:
            await self.bot.say("You don't have any themes set.")
        else:
            dataIO.save_json("data/themes/themes.json", self._themes)
            await self.bot.say("All themes removed.")


def _check_folders():
    fol = "data/themes"
    if not os.path.exists(fol):
        print("Creating {} folder...".format(fol))
        os.makedirs(fol)


def _check_files():
    fil = "data/themes/themes.json"
    if not dataIO.is_valid_json(fil):
        print("Creating default {}...".format(fil))
        dataIO.save_json(fil, {})


def setup(bot):
    _check_folders()
    _check_files()
    bot.add_cog(Theme(bot))
