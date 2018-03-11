from random import randint
from datetime import datetime

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from cogs.utils import checks

from .utils.dataIO import dataIO


class NSStandard:

    def __init__(self, bot):
        self.bot = bot
        self.nsapi = None
        self.illion = ["million", "billion", "trillion", "quadrillion"]
        # Global flag for Z-Day, since I don't see a way to detect it
        # automatically
        self.zday = False

    @commands.command(pass_context=True)
    # API requests: 1; non-API requests: 1
    async def nation(self, ctx, *, nation):
        """Retrieves general info about a specified NationStates nation"""
        self._checks(ctx.prefix)
        nation.strip("\"")
        try:
            data = await self.nsapi.api("category", "demonym2plural", "flag",
                                        "founded", "freedom", "fullname",
                                        "influence", "lastactivity", "motto",
                                        "population", "region", "wa", "zombie"
                                        if self.zday else "fullname",
                                        self.nsapi.shard("census",
                                                         scale="65+66",
                                                         mode="score"),
                                        nation=nation)
        except ValueError:
            embed = discord.Embed(title=nation.replace("_", " ").title(),
                                  url="https://www.nationstates.net/page="
                                  "boneyard?nation={}".format(nation.replace(
                                      " ", "_").lower()),
                                  description="This nation does not exist.")
            embed.set_author(name="NationStates",
                             url="https://www.nationstates.net/")
            embed.set_thumbnail(url="http://i.imgur.com/Pp1zO19.png")
            try:
                return await self.bot.say(embed=embed)
            except discord.HTTPException:
                await self.bot.say(
                    "I need the `Embed links` permission to send this")
        endo = int(float(data["census"]["scale"][1]["score"]))
        if endo == 1:
            endo = "{:d} endorsement".format(endo)
        else:
            endo = "{:d} endorsements".format(endo)
        if data["founded"] == "0":
            data["founded"] = "in Antiquity"
        embed = discord.Embed(
            title=data["fullname"],
            url="https://www.nationstates.net/nation={}".format(data["id"]),
            description="[{}](https://www.nationstates.net/region={})"
                        " | {} {} | Founded {}".format(
                            data["region"],
                            data["region"].lower().replace(" ", "_"),
                            self._illion(data["population"]),
                            data["demonym2plural"], data["founded"]),
            colour=0x8bbc21 if self.zday else randint(0, 0xFFFFFF))
        embed.set_author(name="NationStates Z-Day" if self.zday else
                         "NationStates", url="https://www.nationstates.net/")
        embed.set_thumbnail(url=data["flag"])
        if self.zday:
            embed.add_field(
                name=data["zombie"]["zaction"].title() if
                data["zombie"]["zaction"] else "No Action",
                value="Survivors: {} | Zombies: {} | Dead: {}".format(
                    self._illion(data["zombie"]["survivors"]),
                    self._illion(data["zombie"]["zombies"]),
                    self._illion(data["zombie"]["dead"])), inline=False)
        embed.add_field(name=data["category"], value="{}\t|\t{}\t|\t{}".format(
            data["freedom"]["civilrights"], data["freedom"]["economy"],
            data["freedom"]["politicalfreedom"]), inline=False)
        embed.add_field(name=data["unstatus"],
                        value="{} | {:d} influence ({})".format(
                            endo,
                            int(float(data["census"]["scale"][0]["score"])),
                            data["influence"]), inline=False)
        embed.set_footer(text="Last active {}".format(data["lastactivity"]))
        try:
            await self.bot.say(embed=embed)
        except discord.HTTPException:
            await self.bot.say(
                "I need the `Embed links` permission to send this")

    @commands.command(pass_context=True)
    # API requests: 3; non-API requests: 1
    async def region(self, ctx, *, region):
        """Retrieves general info about a specified NationStates region"""
        self._checks(ctx.prefix)
        region.strip("\"")
        try:
            data = await self.nsapi.api("delegate", "delegateauth", "flag",
                                        "founded", "founder", "lastupdate",
                                        "name", "numnations", "power", "zombie"
                                        if self.zday else "name", region=region)
        except ValueError:
            embed = discord.Embed(title=region.replace("_", " ").title(),
                                  description="This region does not exist.")
            embed.set_author(name="NationStates",
                             url="https://www.nationstates.net/")
            try:
                return await self.bot.say(embed=embed)
            except discord.HTTPException:
                await self.bot.say(
                    "I need the `Embed links` permission to send this")
        if data["delegate"] == "0":
            data["delegate"] = "No Delegate"
        else:
            deldata = await self.nsapi.api("fullname", "influence",
                                           self.nsapi.shard(
                                               "census", scale="65+66",
                                               mode="score"),
                                           nation=data["delegate"])
            endo = int(float(deldata["census"]["scale"][1]["score"]))
            if endo == 1:
                endo = "{:d} endorsement".format(endo)
            else:
                endo = "{:d} endorsements".format(endo)
            data["delegate"] = "[{}](https://www.nationstates.net/nation={})" \
                               " | {} | {:d} influence ({})".format(
                                   deldata["fullname"], data["delegate"], endo,
                                   int(float(
                                       deldata["census"]["scale"]
                                       [0]["score"])),
                                   deldata["influence"])
        if "X" in data["delegateauth"]:
            data["delegateauth"] = ""
        else:
            data["delegateauth"] = " (Non-Executive)"
        if data["founded"] == "0":
            data["founded"] = "in Antiquity"
        if data["founder"] == "0":
            data["founder"] = "No Founder"
        else:
            try:
                data["founder"] = "[{}](https://www.nationstates.net/" \
                                  "nation={})".format((await self.nsapi.api(
                                      "fullname", nation=data["founder"]))
                                      ["fullname"], data["founder"])
            except ValueError:
                data["founder"] = "{} (Ceased to Exist)".format(
                    data["founder"].replace("_", " ").capitalize())
        embed = discord.Embed(
            title=data["name"],
            url="https://www.nationstates.net/region={}".format(data["id"]),
            description="[{} nations](https://www.nationstates.net/region={}"
                        "/page=list_nations) | Founded {} | Power: {}".format(
                            data["numnations"], data["id"], data["founded"],
                            data["power"]),
            colour=0x8bbc21 if self.zday else randint(0, 0xFFFFFF))
        embed.set_author(name="NationStates Z-Day" if self.zday else
                         "NationStates", url="https://www.nationstates.net/")
        if data["flag"]:
            embed.set_thumbnail(url=data["flag"])
        if self.zday:
            embed.add_field(
                name="Zombies",
                value="Survivors: {} | Zombies: {} | Dead: {}".format(
                    self._illion(data["zombie"]["survivors"]),
                    self._illion(data["zombie"]["zombies"]),
                    self._illion(data["zombie"]["dead"])), inline=False)
        embed.add_field(name="Founder", value=data["founder"], inline=False)
        embed.add_field(name="Delegate{}".format(
            data["delegateauth"]), value=data["delegate"], inline=False)
        embed.set_footer(text="Last Updated: {}".format(
            datetime.utcfromtimestamp(int(data["lastupdate"]))))
        try:
            await self.bot.say(embed=embed)
        except discord.HTTPException:
            await self.bot.say(
                "I need the `Embed links` permission to send this")

    def _illion(self, num: str):
        num = int(num)
        index = 0
        while num >= 1000:
            index += 1
            num = num / 1e3
        return "{} {}".format(round(num, 3), self.illion[index])

    def _checks(self, prefix):
        if self.nsapi is None or self.nsapi != self.bot.get_cog("NSApi"):
            self.nsapi = self.bot.get_cog("NSApi")
            if self.nsapi is None:
                raise RuntimeError(
                    "NSApi cog is not loaded. Please ensure it is:\n"
                    "Installed: {p}cog install NationCogs nsapi\n"
                    "Loaded: {p}load nsapi".format(p=prefix))
        self.nsapi.check_agent()


def setup(bot):
    bot.add_cog(NSStandard(bot))
