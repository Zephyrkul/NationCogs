import os

import aiofiles
import discord
from asyncio import Lock
from discord.ext import commands

from __main__ import send_cmd_help
from cogs.utils import checks

from .utils.dataIO import dataIO
from .utils.chat_formatting import box, pagify


class EndoError(Exception):
    pass


class NSEndorse:

    def __init__(self, bot):
        self.bot = bot
        self.nsapi = None
        self.delim = ', '
        self.locks = {"ne": Lock(), "nne": Lock()}

    @commands.command(pass_context=True)
    # API requests: 1; non-API requests: 0
    async def ne(self, ctx, *, wanation):
        """Nations Endorsing the specified WA nation"""
        self._checks(ctx.prefix)
        await self._file(ctx.message.channel,
                         self._endocheck(await self.nsapi.api(
                             "endorsements", "wa", nation=wanation))
                         ["endorsements"].replace(",", self.delim), "ne")

    @commands.command(pass_context=True)
    # API requests: 1; non-API requests: 0
    async def nec(self, ctx, *, wanation):
        """Number of Nations Endorsing (Count) the specified WA nation"""
        self._checks(ctx.prefix)
        await self.bot.say(self._endocheck(await self.nsapi.api(
            "censusscore-66", "wa", nation=wanation))["censusscore"]["text"])

    @commands.command(pass_context=True)
    # API requests: 3; non-API requests: 0
    async def nne(self, ctx, *, wanation):
        """Nations Not Endorsing the specified WA nation"""
        self._checks(ctx.prefix)
        endos = self._endocheck(
            await self.nsapi.api("endorsements", "region", "wa",
                                 nation=wanation))
        nne = (await self._region_wa(endos["region"])).difference(
            "{},{}".format(endos["endorsements"], endos["id"]).split(","))
        await self._file(ctx.message.channel, self.delim.join(nne), "nne")

    @commands.command(pass_context=True)
    # API requests: 3; non-API requests: 0
    async def nnec(self, ctx, *, wanation):
        """Number of Nations Not Endorsing (Count) the specified WA nation"""
        self._checks(ctx.prefix)
        endos = self._endocheck(
            await self.nsapi.api("censusscore-66", "region", "wa",
                                 nation=wanation))
        nne = len(await self._region_wa(endos["region"])) - \
            float(endos["censusscore"]["text"]) - 1
        await self.bot.say("{}.00".format(int(nne)))

    @commands.command(pass_context=True)
    # API requests: 1; non-API requests: 0
    async def spdr(self, ctx, *, nation):
        """The Soft Power Distribution Rating of the specified nation"""
        self._checks(ctx.prefix)
        await self.bot.say((await self.nsapi.api(
            "censusscore-65", nation=nation))["censusscore"]["text"])

    async def _file(self, channel: discord.Channel, text: str, method: str):
        if len(text) < 1024:
            await self.bot.send_message(channel, text)
        else:
            async with self.locks[method]:
                # Not thread-safe, only coroutine-safe
                async with aiofiles.open(
                        "data/nsendorse/{}.txt".format(method),
                        mode="w") as file:
                    await file.write(text)
                await self.bot.send_file(
                    channel, "data/nsendorse/{}.txt".format(method))

    async def _region_wa(self, region):
        rnations = await self.nsapi.api("nations", region=region)
        wamembers = set((await self.nsapi.api(
            "members", council="1"))["members"].split(","))
        return wamembers.intersection(rnations["nations"].split(":"))

    def _endocheck(self, data):
        if data["unstatus"] == "Non-member":
            raise commands.BadArgument("Nation {} is not in the WA.".format(
                data["id"]))
        return data

    def _checks(self, prefix):
        if self.nsapi is None or self.nsapi != self.bot.get_cog('NSApi'):
            self.nsapi = self.bot.get_cog('NSApi')
            if self.nsapi is None:
                raise RuntimeError(
                    "NSApi cog is not loaded. Please ensure it is:\n"
                    "Installed: {p}cog install NationCogs nsapi\n"
                    "Loaded: {p}load nsapi".format(p=prefix))
        self.nsapi.check_agent()


def check_folders():
    fol = "data/nsendorse"
    if not os.path.exists(fol):
        print("Creating {} folder...".format(fol))
        os.makedirs(fol)


def setup(bot):
    check_folders()
    bot.add_cog(NSEndorse(bot))
