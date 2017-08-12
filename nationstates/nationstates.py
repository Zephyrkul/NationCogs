# imports


# exceptions.py


class RateLimitException(Exception):
    def __init__(self, retry_after: float):
        super().__init__(retry_after)
        self.retry_after = retry_after


# ratelimit.py


import time
import bisect
from aiohttp import HTTPException


class _RateLimit:
    def __init__(self):
        self.times = []
        self.xrlrs = 0
        self.block = (50, 30)
        self.limit = self.block[0] - 2
        self.session = None

    def initialize(self, agent: str, loop):
        self.session = aiohttp.ClientSession(loop=loop, headers={
            "User-Agent": agent})

    def __call__(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if "session" in kwargs:
                raise TypeError("kwarg 'session' defined")
            timestamp = time.time()
            self.times = self.times[bisect.bisect_left(
                self.times, timestamp - 30):]
            if len(self.times) > self.limit:
                if self.times:
                    raise RateLimitException(
                        30 - (timestamp - self.times[0]))
                else:
                    self.times = [timestamp] * self.limit
                    raise RateLimitException(30.)
            kwargs["session"] = self.session
            try:
                data = await func(*args, **kwargs)
            except HTTPException as e:
                self.xrlrs = int(e.headers["X-ratelimit-requests-seen"])
                self.times.extend([time.time()] * max(
                    (1, self.xrlrs - len(self.times))))
                raise
            else:
                self.xrlrs = int(data.pop("headers")[
                    "X-ratelimit-requests-seen"])
                self.times.extend([time.time()] * max(
                    (1, self.xrlrs - len(self.times))))
            return data
        return wrapper


RATELIMITED = _RateLimit()


# api.py


import inspect
import zlib
from xml.etree.ElementTree import XMLPullParser
import aiohttp


URL = "https://www.nationstates.net/"
API_URL = "cgi-bin/api.cgi"
CHUNK = 262144


def urlify(s: str):
    return s.lower().replace(" ", "_")


def api(url: str, *args: str, head: bool = False, session: aiohttp.ClientSession = aiohttp.ClientSession(), **kwargs) -> _Request:
    if not args:
        raise TypeError("No *args provided.")
    if not kwargs:
        raise TypeError("No **kwargs provided.")
    kwargs_san = {}
    for k, v in kwargs.items():
        if isinstance(v, str):
            if k.lower() in kwargs_san:
                raise TypeError("Conflicting **kwargs.")
            kwargs_san[k.lower()] = urlify(v)
        else:
            if head:
                raise TypeError("Processor functions not allowed in head requests.")
            if k.upper() in kwargs_san:
                raise TypeError("Conflicting **kwargs.")
            if not callable(v) and not inspect.isawaitable(v):
                raise TypeError("Invalid **kwargs: " + repr(v))
            kwargs_san[k.upper()] = v
    kwargs = kwargs_san
    if url.startswith("?"):
        url = "{}{}{}".format(URL, API_URL, url)
    elif url.startswith("q="):
        # Assume World API
        url = "{}{}?{}".format(URL, API_URL, url)
    elif not url.startswith(URL):
        url = URL + url
    if "q=" not in url and "a=" not in url:
        url = "{}{}q=".format(url, "&" if "?" in url else "?")
    processors = {}
    for s in args:
        url = "{}{}{}".format(url, "+" if not url.endswith("q=") else "", s)
    join = ";" if "q=" in url else "&"
    for k, v in kwargs.items():
        if isinstance(v, str):
            url = "{}{}{}={}".format(url, join, k, v)
        else:
            processors[k] = v
    if "?a=sendTG" in url:
        raise NotImplementedError("The Telegram API is currently not supported.")
    if API_URL in url:
        return _request_api(url, processors, head, session)
    else:
        return _Request(url, processors, head, session)


@RATELIMITED
def _request_api(url: str, processors: dict, head: bool, session: aiohttp.ClientSession) -> _Request:
    return _Request(url, processors, head, session)


class _Request:
    def __init__(self, url: str, processors: dict, head: bool, session: aiohttp.ClientSession):
        self.url = url
        self.processors = processors
        self.head = head
        self.session = session
        self.entered = False
        self.response = None
        self.dobj = None
        self.xpp = None
        self.events = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            if self.entered:
                await self._nextiter()
            else:
                emit = await self._enteriter()
                self.entered = True
                if emit is not None:
                    return emit
                else:
                    await self._nextiter()
        except StopAsyncIteration:
            await self.response.release()
            raise
        except:
            self.response.close()
            raise

    async def _enteriter(self):
        if self.head:
            async with self.session.head(self.url) as response:
                return ("HEAD", response.headers)
        self.response = await self.session.get(self.url)
        self.response.raise_for_status()
        self.dobj = zlib.decompressobj(16 + zlib.MAX_WBITS) if self.response.headers["Content-Type"] == "application/x-gzip" else None
        self.xpp = XMLPullParser(["end"]) if self.dobj or "text/xml" in self.response.headers["Content-Type"] else None
        if not self.xpp:
            self.head = True
            return ("TEXT", await response.text())

    async def _nextiter(self):
        if self.head:
            raise StopAsyncIteration
        if self.events:
            try:
                element = next(self.events)[1]
            except StopIteration:
                pass
            else:
                if element.tag in self.processors:
                    process = self.processors[element.tag]
                    if inspect.isawaitable(process):
                        return (element.tag, await process(element))
                    else:
                        return (element.tag, process(element))
        content = await self.response.content.read(CHUNK)
        if not content:
            raise StopAsyncIteration
        if self.dobj:
            content = self.dobj.decompress(content)
        self.xpp.feed(content.decode("utf-8"))
        self.events = self.xpp.read_events()
        return await self._nextiter()
