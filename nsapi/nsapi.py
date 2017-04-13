import nationstates as ns
import os
import asyncio

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from cogs.utils import checks

from .utils.dataIO import dataIO


class NSApi:

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/nsapi/settings.json")
        self._api = ns.Api(self.settings["AGENT"])

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def agent(self, ctx, *, agent=None):  # API requests: 0; non-API requests: 0
        """Gets or sets the user agent for use with the NationStates API

        Use an informative agent, like an email address, nation name, or both. Contact the cog creator (and unload this cog) if you get any relevant emails or telegrams."""
        if agent is None:
            await self.bot.whisper("```User agent: {}```".format(self._api.user_agent))
            await send_cmd_help(ctx)
        else:
            self.settings["AGENT"] = agent
            dataIO.save_json("data/nsapi/settings.json", self.settings)
            self._api.user_agent = self.settings["AGENT"]
            await self.bot.say("```New user agent: {}```".format(self._api.user_agent))

    def check_agent(self):
        if self._api.user_agent is None:
            raise RuntimeError(
                "User agent is not yet set! Set it with \"[p]agent\" first.")

    def shard(self, shard: str, **kwargs):
        return ns.Shard(shard, **kwargs)

    async def api(self, *shards, **kwargs):
        try:
            if not kwargs:
                return self._api.get_world(list(shards))
            if len(kwargs) != 1:
                raise TypeError("Multiple **kwargs: {}".format(kwargs))
            nation = kwargs.pop("nation", None)
            region = kwargs.pop("region", None)
            council = kwargs.pop("council", None)
            if kwargs:
                raise TypeError("Unexpected **kwargs: {}".format(kwargs))
            run = self.bot.loop.run_in_executor
            if nation:
                task = run(self._api.get_nation(nation, list(shards)))
            if region:
                task = run(self._api.get_region(region, list(shards)))
            if council:
                task = run(self._api.get_wa(council, list(shards)))
            try:
                return await asyncio.wait_for(task, timeout=10)
            except asyncio.TimeoutError:
                await self.bot.say("Error: Request timed out.")
        except ns.NScore.exceptions.NotFound as e:
            raise ValueError(*e.args) from e


def check_folders():
    fol = "data/nsapi"
    if not os.path.exists(fol):
        print("Creating {} folder...".format(fol))
        os.makedirs(fol)


def check_files():
    fil = "data/nsapi/settings.json"
    if not dataIO.is_valid_json(fil):
        print("Creating default {}...".format(fil))
        dataIO.save_json(fil, {"AGENT": ""})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(NSApi(bot))
