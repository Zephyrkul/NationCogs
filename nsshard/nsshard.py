import os
from random import choice

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from cogs.utils import checks

from .utils.dataIO import dataIO


class NSShard:

    def __init__(self, bot):
        self.bot = bot
        self.nsapi = None
        self.delim = '    '
        self.limit = 1018

    @commands.group(aliases=['shards'], pass_context=True)
    async def shard(self, ctx):
        """Retrieves the specified info from NationStates

        Mainly useful if you have the "alias" cog loaded, so that you may set
        custom commands to get shards you are interested in that I haven't made
        a cog for."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @shard.command(name='nation', aliases=['n'], pass_context=True)
    async def _shard_nation(self, ctx, nation, *shards):
        """Retrieves nation shards

        If a provided shard is not on this list or used incorrectly, it will be
        ignored. The nation's ID is always returned.

        name fullname type category wa gavote scvote freedom region population
        tax animal animaltrait currency flag banner banners majorindustry crime
        sensibilities govtpriority govt govdesc industrydesc notable admirable
        founded firstlogin lastlogin lastactivity influence freedomscores
        publicsector deaths leader capital religion customleader customcapital
        customreligion rcensus wcensus censusscore censusscore-N* legislation
        happenings demonym demonym2 demonym2plural factbook factbooklist
        dispatches dispatchlist zombie

        *censusscore-N: Replace "N" with the census ID number, e.g. 66 for WA
        Endorsements"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        self._checks(ctx.prefix)
        if nation[0] == nation[-1] and nation.startswith('"'):
            nation = nation[1:-1]
        data = await self.nsapi.api(*shards, nation=nation)
        strdata = self._dict_format('\n', data)
        if len(strdata) > self.limit:
            format_str = "```{}...```\n\nToo much data. You may view the " \
                         "rest of this data here:\n\nhttps://www." \
                         "nationstates.net/cgi-bin/api.cgi?nation={}&q=" \
                         "{}".format("{}", data["id"], "+".join(shards))
            await self.bot.say(format_str.format(
                strdata[:self.limit - len(format_str) + 8]))
        else:
            await self.bot.say("```{}```".format(strdata))

    @shard.command(name='region', aliases=['r'], pass_context=True)
    async def _shard_region(self, ctx, region, *shards):
        """Retrieves region shards

        If a provided shard is not on this list or used incorrectly, it will be
        ignored. The region's ID is always returned.

        name factbook numnations nations delegatevotes gavote scvote founder
        power flag embassies tags happenings massages* history poll zombie

        *messages: Returns the ten most recent RMB messages, oldest to
        newest"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        self._checks(ctx.prefix)
        if region[0] == region[-1] and region.startswith('"'):
            region = region[1:-1]
        data = await self.nsapi.api(*shards, region=region)
        strdata = self._dict_format('\n', data)
        if len(strdata) > self.limit:
            format_str = "```{}...```\n\nToo much data. You may view the " \
                         "rest of this data here:\n\nhttps://www." \
                         "nationstates.net/cgi-bin/api.cgi?region={}&q=" \
                         "{}".format("{}", data["id"], "+".join(shards))
            await self.bot.say(format_str.format(
                strdata[:self.limit - len(format_str) + 8]))
        else:
            await self.bot.say("```{}```".format(strdata))

    @shard.command(name='world', aliases=['w'], pass_context=True)
    async def _shard_world(self, ctx, *shards):
        """Retrieves world shards

        If a provided shard is not on this list or used incorrectly, it will be
        ignored.

        numations numregions census censusid censussize censusscale
        censusmedian featuredregion newnations regionsbytag poll dispatch
        dispatchlist happenings"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        self._checks(ctx.prefix)
        data = await self.nsapi.api(*shards)
        strdata = self._dict_format('\n', data)
        if len(strdata) > self.limit:
            format_str = "```{}...```\n\nToo much data. You may view the " \
                         "rest of this data here:\n\nhttps://www." \
                         "nationstates.net/cgi-bin/api.cgi?q={}".format(
                             "{}", "+".join(shards))
            await self.bot.say(format_str.format(
                strdata[:self.limit - len(format_str) + 8]))
        else:
            await self.bot.say("```{}```".format(strdata))

    @shard.command(name='wa', aliases=['world_assembly'], pass_context=True)
    async def _shard_wa(self, ctx, council: str, *shards):
        """Retrieves World Assembly shards

        If a provided shard is not on this list or used incorrectly, it will be
        ignored.

        numnations numdelegates delegates members happenings memberlog
        resolution votetrack* dellog* delvotes* lastresolution

        *votetrack, dellog, delvotes: Only valid when used with the
        "resolution" shard"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        self._checks(ctx.prefix)
        if council.lower() == "ga":
            council = "1"
        elif council.lower() == "sc":
            council = "2"
        elif council != '1' and council != '2':
            raise TypeError(
                'Parameter council must be either 1 (GA) or 2 (SC).')
        data = await self.nsapi.api(*shards, council=council)
        strdata = self._dict_format('\n', data)
        if len(strdata) > self.limit:
            format_str = "```{}...```\n\nToo much data. You may view the " \
                         "rest of this data here:\n\nhttps://www." \
                         "nationstates.net/cgi-bin/api.cgi?wa={}&q={}".format(
                             "{}", council, "+".join(shards))
            await self.bot.say(format_str.format(
                strdata[:self.limit - len(format_str) + 8]))
        else:
            await self.bot.say("```{}```".format(strdata))

    def _dict_format(self, base: str, data: dict):
        join = []
        for key, value in data.items():
            if value is None or isinstance(value, (str, int, float)):
                join.append('{} : {}'.format(key, value))
            elif isinstance(value, dict):
                join.append('{} : {}{}{}'.format(
                    key, base, self.delim, self._dict_format(
                        base + self.delim, value)))
            else:
                try:
                    join.append('{} : {}{}{}'.format(
                        key, base, self.delim, self._list_format(
                            base + self.delim, value)))
                except TypeError:
                    join.append('{} : {}'.format(key, value))
        return base.join(join)

    def _list_format(self, base: str, data):
        join = []
        for value in data:
            if value is None or isinstance(value, (str, int, float)):
                join.append(value)
            elif isinstance(value, dict):
                join.append(self.delim + self._dict_format(
                    base + self.delim, value))
            else:
                try:
                    join.append(self.delim + self._list_format(
                        base + self.delim, value))
                except TypeError:
                    join.append(value)
        return base.join(join)

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
    bot.add_cog(NSShard(bot))
