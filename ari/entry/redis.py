import marshal
import random
from typing import List, Optional, Tuple, Union

import aioredis

from ari.redis_lua import RedisLua
from .entry import Entry
from .list import MutEntryListABC, Whence

__all__ = ["RedisEntryList"]


def encode_entry_info(entry: Entry) -> bytes:
    info = [entry.eid]
    return marshal.dumps(info)


def create_entry(aid: str, raw_info: bytes) -> Entry:
    info = marshal.loads(raw_info)
    return Entry(aid, info[0])


GET_ENTRIES: RedisLua[Tuple[List[bytes], List[bytes]]] = RedisLua(b"""
local klist, khash = KEYS[1], KEYS[2]
local start, stop = ARGV[1], ARGV[2]

local aids = redis.call("LRANGE", klist, start, stop)
if #aids == 0 then 
    return {aids, {}}
end

local infos = redis.call("HMGET", khash, unpack(aids))

return {aids, infos}
""")

MOVE_ENTRY: RedisLua[int] = RedisLua(b"""
local function get_index(key, value)
    local l = redis.call("LRANGE", key, 0, -1)
    for i = 1, #l do
        if l[i] == value then
            return i - 1
        end
    end
    
    return -1
end

local klist = KEYS[1]
local aid, index, whence = ARGV[1], tonumber(ARGV[2]), ARGV[3]

local pivot = redis.call("LINDEX", klist, index)
if not pivot then return 0 end

if whence == "absolute" then
    local current_index = get_index(klist, aid)
    if current_index == -1 then return 0 end
    
    if current_index > index then   whence = "BEFORE"
    else                            whence = "AFTER"
    end
elseif whence == "before" or whence == "after" then
    whence = whence:upper()
else                            return 0
end

redis.call("LREM", klist, 1, aid)
redis.call("LINSERT", klist, whence, pivot, aid)

return 1
""")

# Pop an entry from a list
POP_ENTRY: RedisLua[Optional[Tuple[bytes, bytes]]] = RedisLua(b"""
local klist, khash = KEYS[1], KEYS[2]
local pop_command = ARGV[1]

local aid = redis.call(pop_command, klist)
if not aid then return nil end

local info = redis.call("HGET", khash, aid)
redis.call("HDEL", khash, aid)

return {aid, info}
""")

SHUFFLE_ENTRIES = RedisLua(b"""
local function shuffle(l)    
    for i = #l, 2, -1 do
        local j = math.random(i)
        l[i], l[j] = l[j], l[i]
    end
end

local klist = KEYS[1]
local seed = tonumber(ARGV[1])

math.randomseed(seed)

local aids = redis.call("LRANGE", klist, 0, -1)
if #aids == 0 then return end

shuffle(aids)
redis.call("DEL", klist)
redis.call("RPUSH", klist, unpack(aids))
""")


class RedisEntryList(MutEntryListABC):
    """Entry list which uses redis to store the list."""
    __slots__ = ("_redis", "_order_list_key", "_entry_hash_key")

    _redis: aioredis.Redis
    _order_list_key: str
    _entry_hash_key: str

    def __init__(self, redis: aioredis.Redis, key: str) -> None:
        self._redis = redis
        self._order_list_key = f"{key}:order"
        self._entry_hash_key = f"{key}:info"

    async def get_length(self) -> int:
        return await self._redis.llen(self._order_list_key)

    async def get(self, index: Union[int, str, slice]) -> Union[Optional[Entry], List[Entry]]:
        if isinstance(index, slice):
            # stop can't (?) be None
            start, stop, step = index.start, index.stop, index.step
            if start is None:
                start = 0

            if stop is None:
                stop = 0

            if step is None:
                step = 1

            # reversed range
            if start > stop and step < 0:
                start, stop = stop + 1, start
            else:
                # Python ranges are [start, stop), but Redis uses [start, stop]
                stop -= 1

            aids, raw_infos = await GET_ENTRIES(
                self._redis,
                (self._order_list_key, self._entry_hash_key),
                (start, stop),
                encoding=None,
            )

            if step > 0:
                it_data = zip(aids, raw_infos)
            else:
                it_data = zip(reversed(aids), reversed(raw_infos))

            entries = []
            for aid, raw_info in it_data:
                entry = create_entry(aid.decode(), raw_info)
                entries.append(entry)

            return entries

        if isinstance(index, int):
            aid = await self._redis.lindex(self._order_list_key, index, encoding="utf-8")
        elif isinstance(index, str):
            aid = index
        else:
            raise TypeError(f"get() accepts slice, int and str. Got {type(index)}")

        raw_info = await self._redis.hget(f"{self._entry_hash_key}", aid, encoding=None)
        return create_entry(aid, raw_info)

    async def remove(self, entry: Union[Entry, str]) -> bool:
        if isinstance(entry, Entry):
            aid = entry.aid
        else:
            aid = entry

        tr = self._redis.multi_exec()

        rm_fut = tr.lrem(self._order_list_key, 1, aid)
        tr.hdel(self._entry_hash_key, aid)

        await tr.execute()

        return await rm_fut > 0

    async def move(self, entry: Union[Entry, str], index: int, whence: Whence) -> bool:
        if isinstance(entry, Entry):
            aid = entry.aid
        else:
            aid = entry

        res = await MOVE_ENTRY(self._redis,
                               (self._order_list_key,),
                               (aid, index, whence.value))
        return res == 1

    async def add_start(self, entry: Entry) -> None:
        tr = self._redis.multi_exec()

        tr.lpush(self._order_list_key, entry.aid)
        tr.hset(self._entry_hash_key, entry.aid, encode_entry_info(entry))

        await tr.execute()

    async def add_end(self, entry: Entry) -> None:
        tr = self._redis.multi_exec()

        tr.rpush(self._order_list_key, entry.aid)
        tr.hset(self._entry_hash_key, entry.aid, encode_entry_info(entry))

        await tr.execute()

    async def clear(self) -> None:
        await self._redis.delete(self._order_list_key, self._entry_hash_key)

    async def shuffle(self, *, seed: int = None) -> None:
        if seed is None:
            seed = random.getrandbits(16)

        await SHUFFLE_ENTRIES(self._redis,
                              (self._order_list_key,),
                              (seed,))

    async def pop_start(self) -> Optional[Entry]:
        raw_entry = await POP_ENTRY(self._redis,
                                    (self._order_list_key, self._entry_hash_key),
                                    (b"LPOP",),
                                    encoding=None)
        if raw_entry:
            return create_entry(raw_entry[0].decode(), raw_entry[1])
        else:
            return None

    async def pop_end(self) -> Optional[Entry]:
        raw_entry = await POP_ENTRY(self._redis,
                                    (self._order_list_key, self._entry_hash_key),
                                    (b"RPOP",),
                                    encoding=None)
        if raw_entry:
            return create_entry(raw_entry[0].decode(), raw_entry[1])
        else:
            return None
