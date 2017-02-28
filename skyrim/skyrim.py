import os
from random import choice

import discord
from discord.ext import commands

from .utils.dataIO import dataIO


class GuardLines:

    def __init__(self, bot):
        self.bot = bot
        self.lines = dataIO.load_json("data/skyrim/lines.json")

    @commands.command()
    async def guard(self):
        """Says a random guard line from Skyrim"""
        await self.bot.say(choice(self.lines))

def check_folders():
    if not os.path.exists("data/skyrim/"):
        print("Creating data/skyrim/ folder...")
        os.makedirs("data/skyrim/")

def check_files():
    """Makes sure the cog data exists"""
    if not os.path.isfile("data/skyrim/lines.json"):
        raise RuntimeError("Required data is missing. Please reinstall this cog.")

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(GuardLines(bot))
