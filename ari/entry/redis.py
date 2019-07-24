from typing import List, Optional, Union

import aioredis

from .entry import Entry
from .list import MutEntryListABC

__all__ = ["RedisEntryList", "encode_entry", "decode_entry", "maybe_decode_entry"]


def encode_entry(entry: Entry) -> str:
    return f"{entry.aid},{entry.eid}"


def decode_entry(data: str) -> Entry:
    aid, eid = data.split(",", 1)
    return Entry(aid, eid)


def maybe_decode_entry(data: Optional[str]) -> Optional[Entry]:
    if not data:
        return None
    else:
        return decode_entry(data)


# TODO use ordered set for aids and {aid: details like eid} hash map
class RedisEntryList(MutEntryListABC):
    """Entry list which uses redis to store the list."""

    __slots__ = ("_redis", "_list_key")

    _redis: aioredis.Redis
    _list_key: str

    def __init__(self, redis: aioredis.Redis, queue_key: str) -> None:
        self._redis = redis
        self._list_key = queue_key

    async def get_length(self) -> int:
        return await self._redis.llen(self._list_key)

    async def get(self, index: Union[int, slice]) -> Union[Optional[Entry], List[Entry]]:
        if isinstance(index, int):
            return maybe_decode_entry(await self._redis.lindex(self._list_key, index, encoding="utf-8"))
        else:
            # stop can't (?) be None
            start, stop, step = index.start, index.stop, index.step
            if start is None:
                start = 0

            if step is None:
                step = 1

            # reversed range
            if start > stop and step < 0:
                start, stop = stop, start

            # Python ranges are [start, stop), but Redis uses [start, stop]
            entries = await self._redis.lrange(self._list_key, start, stop - 1)
            return list(map(decode_entry, entries[::step]))

    async def remove(self, entry: Union[Entry, str]) -> bool:
        if isinstance(entry, str):
            entry = await self.get_entry(entry)

        await self._redis.lrem(self._list_key, 1, encode_entry(entry))

    async def move(self, entry: Union[Entry, str], to_index: int) -> bool:
        # TODO use Lua
        raise NotImplementedError

    async def add_start(self, entry: Entry) -> None:
        await self._redis.lpush(self._list_key, encode_entry(entry))

    async def add_end(self, entry: Entry) -> None:
        await self._redis.rpush(self._list_key, encode_entry(entry))

    async def clear(self) -> None:
        await self._redis.delete(self._list_key)

    async def shuffle(self) -> None:
        # TODO use Lua
        raise NotImplementedError

    async def pop_start(self) -> Optional[Entry]:
        return maybe_decode_entry(await self._redis.lpop(self._list_key, encoding="utf-8"))

    async def pop_end(self) -> Optional[Entry]:
        return maybe_decode_entry(await self._redis.rpop(self._list_key, encoding="utf-8"))
