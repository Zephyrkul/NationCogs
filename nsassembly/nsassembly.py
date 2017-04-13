from html import unescape
from random import randint
from datetime import datetime, timezone

import discord
from discord.ext import commands
from .utils.chat_formatting import pagify


class NSAssembly:

    def __init__(self, bot):
        self.bot = bot
        self.nsapi = None

    @commands.group(pass_context=True)
    async def ga(self, ctx):  # API requests: 2; non-API requests: 2
        """Retrieves info on the current General Assembly resolution"""
        res = await self._res_format(ctx, sc=False)
        message = None
        for page in res[0]:
            if page is not None:
                message = await self.bot.say(page)
        try:
            if message is None:
                await self.bot.say(embed=res[1])
            else:
                await self.bot.edit_message(message, embed=res[1])
        except discord.HTTPException:
            await self.bot.say(
                "I need the `Embed links` permission to send this")

    @ga.command(name="resolution")
    async def _ga_resolution(self):  # API requests: 2; non-API requests: 2
        """Also retrieves the resolution text"""
        pass

    @ga.command(name="delegate")
    async def _ga_delegate(self):  # API requests: 2; non-API requests: 2
        """Also retrieves the top Delegate votes"""
        pass

    @commands.group(pass_context=True)
    async def sc(self, ctx):  # API requests: 2; non-API requests: 2
        """Retrieves info on the current Security Council resolution"""
        res = await self._res_format(ctx, sc=True)
        message = None
        for page in res[0]:
            if page is not None:
                message = await self.bot.say(page)
        try:
            if message is None:
                await self.bot.say(embed=res[1])
            else:
                await self.bot.edit_message(message, embed=res[1])
        except discord.HTTPException:
            await self.bot.say(
                "I need the `Embed links` permission to send this")

    @sc.command(name="resolution")
    async def _sc_resolution(self):  # API requests: 2; non-API requests: 2
        """Also retrieves the resolution text"""
        pass

    @sc.command(name="delegate")
    async def _sc_delegate(self):  # API requests: 2; non-API requests: 2
        """Also retrieves the top Delegate votes"""
        pass

    async def _res_format(self, ctx, *, sc: bool):
        self._checks(ctx.prefix)
        delegate = str(ctx.invoked_subcommand).lower() == "{} delegate".format(
            "sc" if sc else "ga")
        data = await self.nsapi.api(
            "resolution", "delvotes" if delegate else "resolution",
            "lastresolution", council="2" if sc else "1")
        if data["resolution"] is None:
            out = unescape(data["lastresolution"]).replace(
                "<strong>", "**").replace("</strong>", "**")
            try:
                out = "{}[{}](https://www.nationstates.net{}){}".format(
                    out[:out.index("<a")],
                    out[out.index("\">") + 2:out.index("</a")],
                    out[out.index("=\"") + 2:out.index("\">")],
                    out[out.index("</a>") + 4:])
            except ValueError:
                pass
            embed = discord.Embed(title="Last Resolution", description=out,
                                  colour=randint(0, 0xFFFFFF))
            embed.set_thumbnail(
                url="http://i.imgur.com/{}.jpg".format(
                    "4dHt6si" if sc else "7EMYsJ6"))
            return ([None], embed)
        data = data["resolution"]
        if delegate:
            data["delvotes_for"]["delegate"].sort(
                key=lambda k: int(k["votes"]), reverse=True)
            data["delvotes_against"]["delegate"].sort(
                key=lambda k: int(k["votes"]), reverse=True)
            if len(data["delvotes_for"]["delegate"]) > 10:
                del data["delvotes_for"]["delegate"][10:]
            if len(data["delvotes_against"]["delegate"]) > 10:
                del data["delvotes_against"]["delegate"][10:]
        embed = discord.Embed(
            title=data["name"],
            url="https://www.nationstates.net/page=UN_delegate_votes/"
                "council={}".format(2 if sc else 1) if delegate else
            "https://www.nationstates.net/page={}".format("sc" if sc else "ga"),
            description="Category: {}".format(data["category"]),
            colour=randint(0, 0xFFFFFF))
        authdata = await self.nsapi.api(
            "fullname", "flag", nation=data["proposed_by"])
        embed.set_author(name=authdata["fullname"],
                         url="https://www.nationstates.net/nation={}".format(
                             data["proposed_by"]), icon_url=authdata["flag"])
        embed.set_thumbnail(
            url="http://i.imgur.com/{}.jpg".format(
                "4dHt6si" if sc else "7EMYsJ6"))
        message = [None]
        if delegate:
            embed.add_field(name="Top Delegates For", value="\t|\t".join(
                ["[{}](https://www.nationstates.net/nation={}) ({})".format(
                    d["nation"].title().replace("_", " "), d["nation"],
                    d["votes"]) for d in data["delvotes_for"]["delegate"]]),
                            inline=False)
            embed.add_field(name="Top Delegates Against", value="\t|\t".join(
                ["[{}](https://www.nationstates.net/nation={}) ({})".format(
                    d["nation"].title().replace("_", " "), d["nation"],
                    d["votes"]) for d in data["delvotes_against"]["delegate"]]),
                            inline=False)
        elif str(ctx.invoked_subcommand).lower() == "{} resolution".format(
                "sc" if sc else "ga"):
            desc = unescape(data["desc"]).replace("[i]", "*").replace(
                "[/i]", "*").replace("[b]", "**").replace(
                    "[/b]", "**").replace("[u]", "__").replace(
                        "[/u]", "__").replace("&#39;", "'").replace(
                            "&quot;", "\"")
            if len(desc) > 1000:
                message = pagify(desc)
            else:
                embed.add_field(name="Resolution", value=desc, inline=False)
        percent = 100 * float(data["total_votes_for"]) / (
            float(data["total_votes_for"]) + float(data["total_votes_against"]))
        embed.add_field(name="Total Votes",
                        value="For {}\t{:◄<13}\t{} Against".format(
                            data["total_votes_for"], "►" *
                            int(round(percent / 10)) +
                            str(int(round(percent))) + "%",
                            data["total_votes_against"]))
        embed.set_footer(text=datetime.fromtimestamp(float(
            data["promoted"]), timezone.utc).strftime(
                "Voting began %a, %d %b %Y %H:%M:%S GMT"))
        return (message, embed)

    def _checks(self, prefix):
        if self.nsapi is None or self.nsapi != self.bot.get_cog('NSApi'):
            self.nsapi = self.bot.get_cog('NSApi')
            if self.nsapi is None:
                raise RuntimeError(
                    "NSApi cog is not loaded. Please ensure it is:\n"
                    "Installed: {p}cog install NationCogs nsapi\n"
                    "Loaded: {p}load nsapi".format(p=prefix))
        self.nsapi.check_agent()


def setup(bot):
    bot.add_cog(NSAssembly(bot))
