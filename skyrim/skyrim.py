import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from random import choice
import os


class GuardLines:
    """Edited from Airenkun's Insult Cog from 26-Cogs"""

    def __init__(self, bot):
        self.bot = bot
        self.lines = fileIO("data/skyrim/lines.json", "load")

    @commands.command()
    async def guard(self):
        """Says a random guard line from Skyrim"""
        await self.bot.say(choice(self.lines))

def check_folders():
    folders = ("data", "data/skyrim/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)

def check_files():
    """Moves the file from cogs to the data directory. Important -> Also changes the name to lines.json"""
    lines = {"I used to be an adventurer like you. Then I took an arrow in the knee..."}

    if not os.path.isfile("data/skyrim/lines.json"):
        if os.path.isfile("cogs/put_in_cogs_folder.json"):
            print("moving default lines.json...")
            os.rename("cogs/put_in_cogs_folder.json", "data/skyrim/lines.json")
        else:
            print("creating default lines.json...")
            fileIO("data/skyrim/lines.json", "save", lines)

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(GuardLines(bot))