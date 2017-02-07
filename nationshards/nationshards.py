try:
    import nationstates as ns
except:
    ns = None
import discord
import os
from .utils.chat_formatting import pagify, box
from cogs.utils import checks
from discord.ext import commands
from .utils.dataIO import dataIO
from __main__ import send_cmd_help
from random import choice

class NationShards:

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/nationstates/settings.json')
        self.api = ns.Api(self.settings['AGENT'])

    @commands.group(aliases=['shards'], pass_context=True)
    async def shard(self, ctx):
        """Retrieves the specified info from NationStates

        Note that some shards provide a lot of data at once; have [p]restart prepared just in case."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @shard.command(name='agent', aliases=['a'], pass_context=True)
    @checks.is_owner()
    async def _shard_agent(self, ctx, *, agent : str = None):
        """Gets or sets the user agent for use with the NationStates API

        Use an informative agent, like an email address. Contact the cog creator (and disable this cog) if you get any threatening emails."""
        if agent is None:
            self.settings = dataIO.load_json('data/nationstates/settings.json')
            if self.settings['AGENT'] != self.api.user_agent:
                await self.bot.say(box('User agent change detected. Updating...', lang='diff'))
                self.api.user_agent = self.settings['AGENT']
            await self.bot.whisper(box('User agent: %s' % self.api.user_agent, lang='diff'))
            await send_cmd_help(ctx)
        else:
            self.settings['AGENT'] = agent
            dataIO.save_json('data/nationstates/settings.json', self.settings)
            self.api.user_agent = self.settings['AGENT']
            await self.bot.say(box('New user agent: %s' % self.api.user_agent, lang='diff'))

    @shard.command(name='nation', aliases=['n'], pass_context=True)
    async def _shard_nation(self, ctx, nation, *shards):
        """Retrieves nation shards

        If a shard not on this list is provided, it will be ignored. The 'id' shard is always returned.

        name fullname type category wa gavote scvote freedom region population tax animal animaltrait currency flag banner banners majorindustry crime sensibilities govtpriority govt govdesc industrydesc notable admirable founded firstlogin lastlogin lastactivity influence freedomscores publicsector deaths leader capital religion customleader customcapital customreligion rcensus wcensus censusscore censusscore-N legislation happenings demonym demonym2 demonym2plural factbook factbooklist dispatches dispatchlist zombies"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        if self.api.user_agent is None:
            await self.bot.say('User agent is not yet set! Set it with `[p]agent` first.')
            return
        if nation[0] == nation[-1] and nation.startswith('"'):
            nation = nation[1:-1]
        try:
            data = self.api.get_nation(nation, list(shards))
            for page in pagify(self._dict_format('\n',data.collect()), ['\n', '[', ':'], shorten_by=16):
                await self.bot.say(box(page.lstrip(' '), lang='diff'))
        except ns.NScore.exceptions.NotFound:
            await self.bot.say('`Nation "%s" does not exist`' % nation)

    @shard.command(name='region', aliases=['r'], pass_context=True)
    async def _shard_region(self, ctx, region, *shards):
        """Retrieves region shards

        If a shard not on this list is provided, it will be ignored. The 'id' shard is always returned.

        name factbook numnations nations delegatevotes gavote scvote founder power flag embassies tags happenings massages history poll"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        if self.api.user_agent is None:
            await self.bot.say('User agent is not yet set! Set it with `[p]agent` first.')
            return
        if region[0] == region[-1] and region.startswith('"'):
            region = region[1:-1]
        try:
            data = self.api.get_region(region, list(shards))
            for page in pagify(self._dict_format('\n',data.collect()), ['\n', '[', ':'], shorten_by=16):
                await self.bot.say(box(page.lstrip('\n'), lang='diff'))
        except ns.NScore.exceptions.NotFound:
            await self.bot.say('`Region "%s" does not exist`' % region)

    @shard.command(name='world', aliases=['w'], pass_context=True)
    async def _shard_world(self, ctx, *shards):
        """Retrieves world shards

        If a shard not on this list is provided, it will be ignored.

        numations numregions census censusid censussize censusscale censusmedian featuredregion newnations regionsbytag poll dispatch dispatchlist happenings"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        if self.api.user_agent is None:
            await self.bot.say('User agent is not yet set! Set it with `[p]agent` first.')
            return
        try:
            data = self.api.get_world(list(shards))
            for page in pagify(self._dict_format('\n',data.collect()), ['\n', '[', ':'], shorten_by=16):
                await self.bot.say(box(page.lstrip(' '), lang='diff'))
        except ns.NScore.exceptions.APIError:
            await self.bot.say('`No valid shards were provided`')

    @shard.command(name='wa', aliases=['world_assembly'], pass_context=True)
    async def _shard_wa(self, ctx, council : str, *shards):
        """Retrieves World Assembly shards

        If a shard not on this list is provided, it will be ignored.

        numnations numdelegates delegates members happenings memberlog resolution votetrack dellog delvotes lastresolution"""
        if len(shards) == 0:
            await send_cmd_help(ctx)
            return
        if self.api.user_agent is None:
            await self.bot.say('User agent is not yet set! Set it with `[p]agent` first.')
            return	
        if council != '1' and council != '2':
            raise TypeError('Parameter council must be either 1 (GA) or 2 (SC).')
        try:
            data = self.api.get_wa(council, list(shards))
            for page in pagify(self._dict_format('\n',data.collect()), ['\n', '[', ':'], shorten_by=16):
                await self.bot.say(box(page.lstrip(' '), lang='diff'))
        except ns.NScore.exceptions.APIError:
            await self.bot.say('`No valid shards were provided`')

    def _dict_format(self, base : str, data : dict):
        return base.join('%s : %s'%(key,'%s >%s'%(base, self._dict_format('%s >'%base,value) if isinstance(value,dict) else value)) for key,value in data.items())

def check_folders():
    if not os.path.exists('data/nationstates'):
        print('Creating data/nationstates folder...')
        os.makedirs('data/nationstates')

def check_files():
    f = 'data/nationstates/settings.json'
    data = {'AGENT' : ''}
    if not dataIO.is_valid_json(f):
        dataIO.save_json(f, data)

def setup(bot):
    if ns is None:
        raise RuntimeError('You\'re missing the NationStates library.\nInstall it with "pip install nationstates" and reload the module.')
    check_folders()
    check_files()
    bot.add_cog(NationShards(bot))
