from enum import Enum
from collections import deque
import time
import bisect
import functools
import inspect
import zlib
from urllib.parse import urlparse, urlunparse
from aiohttp import ClientSession
from aiohttp.errors import HttpProcessingError
from lxml.etree import XMLPullParser, HTMLPullParser


SCHEME = "https"
NETLOC = "www.nationstates.net"
APIPATH = "/cgi-bin/api.cgi"


class RateLimitException(Exception):
    """Exception raised when exceeding the NationStates rate limit."""

    def __init__(self, retry_after: float):
        super().__init__(retry_after)
        self.retry_after = retry_after


class _RateLimit(object):
    def __init__(self):
        self.xrlrs = 0
        self.apitimes = deque()
        self.htmltimes = deque()
        self.apiblock = (50, 30)
        self.htmlblock = (10, 60)

    def __call__(self, function):
        @functools.wraps(function)
        async def _wrapper(*args, **kwargs):
            instance = args[0]
            if APIPATH in instance.url:
                times = self.apitimes
                block = self.apiblock
            else:
                times = self.htmltimes
                block = self.htmlblock
            timestamp = time.time()
            del times[:bisect.bisect_left(times, timestamp - block[1])]
            if len(times) > block[0]:
                raise RateLimitException(block[1] - (timestamp - times[0]))
            try:
                headers = await function(*args, **kwargs)
            except HttpProcessingError as e:
                self._addtime(times, e.headers)
                raise
            else:
                self._addtime(times, headers)
        return _wrapper

    def _addtime(self, times, headers):
        timestamp = time.time()
        try:
            xrlrs = int(headers["X-ratelimit-requests-seen"])
        except KeyError:
            xrlrs = None
        if xrlrs:
            times.extend([timestamp] * max((1, xrlrs - len(times))))
        else:
            times.append(timestamp)


RATELIMITED = _RateLimit()


class _Request:
    def __init__(self, url: str, processors: dict, head: bool, session: ClientSession):
        self.url = url
        self.processors = processors
        self.head = head
        self.session = session
        self.entered = False
        self.response = None
        self.dobj = None
        self.parser = None
        self.charset = None
        self.events = None

    def __aiter__(self):
        return self

    async def __anext__(self) -> tuple:
        try:
            if self.entered:
                await self._nextiter()
            else:
                self.entered = True
                return await self._enteriter()
        except StopAsyncIteration:
            if self.parser:
                self.parser.close()
            await self.response.release()
            raise
        except:
            if self.parser:
                self.parser.close()
            if self.response:
                self.response.close()
            raise

    @RATELIMITED
    async def _request(self) -> dict:
        self.response = await self.session.head(self.url) if self.head else await self.session.get(self.url)
        self.response.raise_for_status()
        return self.response.headers

    async def _enteriter(self) -> tuple:
        await self._request()
        contenttype = self.response.headers["Content-Type"].split("; ")
        self.dobj = zlib.decompressobj(16 + zlib.MAX_WBITS) if contenttype[0] == "application/x-gzip" else None
        self.parser = XMLPullParser(["end"]) if self.dobj or contenttype[0] == "text/xml" else \
            HTMLPullParser(["end"]) if contenttype[0] == "text/html" else None
        self.charset = contenttype[1][contenttype[1].index("=") + 1:] if len(contenttype) > 1 else "utf-8"
        if self.head:
            return ("@HEAD", self.response.headers)
        else:
            return await self._nextiter()

    async def _nextiter(self) -> tuple:
        if self.head:
            raise StopAsyncIteration
        if not self.parser:
            self.head = True
            return ("#BYTES", await self.response.read())
        if self.events:
            try:
                element = next(self.events)[1]
            except StopIteration:
                pass
            else:
                if not self.processors:
                    return (element.tag, element)
                if element.tag in self.processors:
                    process = self.processors[element.tag.lower()]
                    if process is None:
                        return (element.tag, element)
                    if inspect.isawaitable(process):
                        return (element.tag, await process(element))
                    return (element.tag, process(element))
        content = await self.response.content.readany()
        if not content:
            raise StopAsyncIteration
        if self.dobj:
            content = self.dobj.decompress(content)
        self.parser.feed(content.decode(self.charset))
        self.events = self.parser.read_events()
        return await self._nextiter()


def request(url: str, *args: str, head: bool=False, session: ClientSession=ClientSession(), **kwargs) -> _Request:
    """Forms an HTTP GET or HEAD request to the NationStates site or API.

    While this method is synchronous, it returns an asynchronous iterator.
    So, while you *can* do the following::

        request = nationstates.request(...)

    You will still have to use asynchronous iteration to get the actual data::

        async for event, result in request:
            ...

    The actual request will not be opened until it is iterated over; thus you
    can prepare several requests ahead of time and space out the
    requests themselves.

    This wrapper supports the API ratelimit automatically.

    Parameters:
        url: The URL to request.
            If `url` starts with `"?"`, it is considered an API request.
            If `url` starts with `"q="`, it is considered a World API request.
            Otherwise, the NationStates base site is prepended if absent.
        *args: The shards to request from the NationStates API.
            If `url` does not lead to an API request, these are ignored.

    Keyword Arguments:
        head: Make an HTTP HEAD request instead if this is True.
        session:
            The `ClientSession` to use. Defaults to a global session.
        **kwargs: Keyword arguments.
            If the value is a String, assume it's a URL parameter.
            If the value is callable or awaitable, assume it's a processor.
            In the latter case, the iterator will take any HTML / XML Elements
            matching the keyword key and pass the Element object into
            the callable / awaitable and call / await it.
            If None is instead passed, it will return the Element raw.
            If no processors are specified, all Elements are returned raw.

    Returns:
        An asynchronous iterator.

    Yields:
        tuple: A tuple with the event (the requested HTML / XML element or
            other events) and the processed HTML / XML element.
    """
    # Process **kwargs
    shardkwargs = {}
    processors = {}
    for k, v in kwargs.items():
        k = k.lower()
        if isinstance(v, str):
            if k in shardkwargs:
                raise TypeError("Conflicting **kwargs: {!r} {!r}.".format(v, shardkwargs[k]))
            shardkwargs[k] = v
        else:
            if head:
                raise TypeError("Processor functions not allowed in head requests.")
            if k in processors:
                raise TypeError("Conflicting **kwargs: {!r} {!r}.".format(v, processors[k]))
            if v is not None and not callable(v) and not inspect.isawaitable(v):
                raise TypeError("Invalid **kwargs: " + repr(v))
            processors[k] = v
    del kwargs
    # Process url
    if url.startswith(("q=", "a=")):
        url = "?" + url
    url = list(urlparse(url))
    if "a=sendTG" in url[4]:
        raise NotImplementedError("The Telegram API is currently not supported.")
    if url[1] != NETLOC and url[1] != NETLOC[4:]:
        raise ValueError("I will only request from the NationStates site at " + NETLOC)
    url[0], url[1], url[2] = SCHEME, NETLOC, url[2] if url[2] else APIPATH
    queries = url[4].split("&")
    shardquery = [i for i in range(len(queries)) if queries[i].startswith("q=")]
    if not shardquery and args:
        queries.append("q=" + "+".join(args))
    elif shardquery and args:
        queries[shardquery[0]] += "+" + "+".join(args))
    if shardkwargs:
        queries[-1] += ";".join("{}={}".format(k, v) for k, v in shardkwargs.items())
    url[4] = "&".join(queries)
    return _Request(urlunparse(url), processors, head, session)
