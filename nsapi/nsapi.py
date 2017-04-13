import os
from time import time
from asyncio import wait_for, TimeoutError
from functools import partial
from nationstates import Api, Shard
from nationstates.NScore.exceptions import NotFound, RateLimitCatch

import discord
from discord.ext import commands

from __main__ import send_cmd_help
from cogs.utils import checks

from .utils.dataIO import dataIO


class NSApi:

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json("data/nsapi/settings.json")
        self._api = Api()

    @commands.command(pass_context=True)
    @checks.is_owner()
    # API requests: 0; non-API requests: 0
    async def agent(self, ctx, *, agent=None):
        """Gets or sets the user agent for use with the NationStates API

        Use an informative agent, like an email address, nation name, or both.
        Contact the cog creator (and unload this cog) if you get any relevant
        emails or telegrams."""
        if not agent:
            await self.bot.whisper("```User agent: {}```".format(
                self.settings["AGENT"]))
            await send_cmd_help(ctx)
        else:
            self.settings["AGENT"] = agent
            dataIO.save_json("data/nsapi/settings.json", self.settings)
            await self.bot.say("```New user agent: {}```".format(
                self.settings["AGENT"]))

    def check_agent(self):
        if not self.settings["AGENT"]:
            raise RuntimeError(
                "User agent is not yet set! Set it with \"[p]agent\" first.")

    def shard(self, shard: str, **kwargs):
        return Shard(shard, **kwargs)

    async def api(self, *shards, **kwargs):
        self.check_agent()
        args = {"shard": list(shards), "user_agent": self.settings["AGENT"],
                "auto_load": True, "version": "9", "use_error_xrls": True,
                "use_error_rl": True}
        try:
            if not kwargs:
                args["api"] = "world"
            elif len(kwargs) != 1:
                raise TypeError("Multiple **kwargs: {}".format(kwargs))
            else:
                nation = kwargs.pop("nation", None)
                region = kwargs.pop("region", None)
                council = kwargs.pop("council", None)
                if kwargs:
                    raise TypeError("Unexpected **kwargs: {}".format(kwargs))
                if nation:
                    args.update(api="nation", value=nation)
                if region:
                    args.update(api="region", value=region)
                if council:
                    args.update(api="wa", value=council)
            part = partial(self._api.request, **args)
            try:
                ret = await wait_for(self.bot.loop.run_in_executor(
                    None, part), timeout=10)
                return ret.collect()
            except TimeoutError:
                await self.bot.say("Error: Request timed out.")
                raise
        except NotFound as e:
            raise ValueError(*e.args) from e
        except RateLimitCatch as e:
            await self.bot.say(" ".join(e.args))
            retry_after = 30. - (time() - min(self._api.get_ratelimit()))
            raise commands.CommandOnCooldown(30, retry_after)


def check_folders():
    fol = "data/nsapi"
    if not os.path.exists(fol):
        print("Creating {} folder...".format(fol))
        os.makedirs(fol)


def check_files():
    fil = "data/nsapi/settings.json"
    if not dataIO.is_valid_json(fil):
        print("Creating default {}...".format(fil))
        dataIO.save_json(fil, {"AGENT": None})


def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(NSApi(bot))
