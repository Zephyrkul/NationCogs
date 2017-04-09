import os
from copy import deepcopy
from random import choice

import discord
from discord.ext import commands

from .utils.dataIO import dataIO
from __main__ import send_cmd_help


class Theme:
    def __init__(self, bot):
        self.bot = bot
        self.themes = dataIO.load_json("data/themes/themes.json")

    @commands.command(pass_context=True, no_pm=True)
    async def theme(self, ctx, user: discord.Member=None):
        """Plays one of your themes, or one of the specified user's."""
        user = user if user else ctx.message.author
        if user != self.bot.user and (user.id not in self.themes or
                                      not self.themes[user.id]):
            return await self.bot.say("{} has no themes set.".format(
                user.display_name))
        server = ctx.message.server
        content = ctx.message.content
        message = deepcopy(ctx.message)
        prefix = next((p for p in self.bot.settings.get_prefixes(server) if
                       content.startswith(p)))
        message.content = prefix + "sing" if user == self.bot.user else \
            "{}play {}".format(prefix, choice(self.themes[user.id]))
        await self.bot.process_commands(message)

    @commands.group(pass_context=True)
    async def themeset(self, ctx):
        """Configure your themes."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            try:
                await self.bot.say("```Your themes: {}```".format(", ".join(
                    self.themes[ctx.message.author.id])))
            except KeyError:
                pass

    @themeset.command(name="add", pass_context=True)
    async def _themeset_add(self, ctx, theme):
        """Adds the specified theme to your themes."""
        self.themes.setdefault(ctx.message.author.id, []).append(theme)
        dataIO.save_json("data/themes/themes.json", self.themes)
        await self.bot.say("Theme added.")

    @themeset.command(name="remove", pass_context=True)
    async def _themeset_remove(self, ctx, theme):
        """Removes the specified theme from your themes."""
        try:
            self.themes[ctx.message.author.id].remove(theme)
        except KeyError:
            await self.bot.say("You don't have any themes set.")
        except ValueError:
            await self.bot.say("That theme isn't in your list of themes")
        else:
            dataIO.save_json("data/themes/themes.json", self.themes)
            await self.bot.say("Theme removed.")

    @themeset.command(name="clear", pass_context=True)
    async def _themeset_clear(self, ctx):
        """Removes all of your set themes."""
        try:
            del self.themes[ctx.message.author.id]
        except KeyError:
            await self.bot.say("You don't have any themes set.")
        else:
            dataIO.save_json("data/themes/themes.json", self.themes)
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
