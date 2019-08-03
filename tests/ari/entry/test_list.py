import asyncio
import itertools
from typing import Optional, Set, Tuple, List, Iterable

import aioredis
import pytest

import ari

pytestmark = pytest.mark.asyncio

list_id = 0


# redefine the event loop fixture to be module-wide
@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def redis() -> aioredis.Redis:
    try:
        r = await aioredis.create_redis("redis://localhost")
    except OSError:
        pytest.skip("no redis instance")
    else:
        print("flushing redis")
        await r.flushall()
        return r


def get_redis_list(redis: aioredis.Redis) -> ari.RedisEntryList:
    global list_id

    key = f"ari:lists:{list_id}"
    list_id += 1
    return ari.RedisEntryList(redis, key)


@pytest.fixture()
async def redis_list(redis: aioredis.Redis) -> ari.RedisEntryList:
    return get_redis_list(redis)


async def add_entries(l: ari.MutEntryListABC, *entries: ari.Entry) -> None:
    for entry in entries:
        await l.add_end(entry)


def create_entry(aid: str) -> ari.Entry:
    return ari.Entry(aid, f"entry-{aid}")


def create_entries(aids: Iterable[str]) -> List[ari.Entry]:
    return list(map(create_entry, aids))


ABCD = create_entries("abcd")
ENTRY_A, ENTRY_B, ENTRY_C, ENTRY_D = ABCD


async def test_list_get(redis_list: ari.RedisEntryList) -> None:
    await add_entries(redis_list, *ABCD)

    assert await redis_list.get(0) == ENTRY_A
    assert await redis_list.get(-1) == ENTRY_D

    assert await redis_list.get(ENTRY_B.aid) == ENTRY_B

    assert await redis_list[:] == ABCD
    assert await redis_list[:2] == ABCD[:2]
    assert await redis_list[2:2] == ABCD[2:2]
    assert await redis_list[2:] == ABCD[2:]

    assert await redis_list[1:-1] == ABCD[1:-1]
    assert await redis_list[::-1] == ABCD[::-1]
    assert await redis_list[3:1:-1] == ABCD[3:1:-1]
    assert await redis_list[-1:-5:-1] == ABCD[-1:-5:-1]


async def test_list_add(redis_list: ari.RedisEntryList) -> None:
    await redis_list.add_start(ENTRY_A)
    await redis_list.add_end(ENTRY_B)
    await redis_list.add_end(ENTRY_C)
    await redis_list.add_start(ENTRY_D)

    assert await redis_list.get(slice(None)) == [ENTRY_D, ENTRY_A, ENTRY_B, ENTRY_C]


async def test_list_remove(redis_list: ari.RedisEntryList) -> None:
    await add_entries(redis_list, *ABCD)
    assert await redis_list.remove(ENTRY_C)
    assert await redis_list.remove(ENTRY_A.aid)

    assert not await redis_list.remove("entry which doesn't exist")

    assert await redis_list[:] == [ENTRY_B, ENTRY_D]


async def test_list_length(redis_list: ari.RedisEntryList):
    assert await redis_list.get_length() == 0
    await add_entries(redis_list, *ABCD)
    assert await redis_list.get_length() == len(ABCD)


async def test_list_clear(redis_list: ari.RedisEntryList):
    await add_entries(redis_list, *ABCD)
    await redis_list.clear()
    assert await redis_list[:] == []


async def test_list_pop(redis_list: ari.RedisEntryList):
    await add_entries(redis_list, *ABCD)

    assert await redis_list.pop_end() == ENTRY_D
    assert await redis_list.pop_start() == ENTRY_A
    assert await redis_list.pop_start() == ENTRY_B
    assert await redis_list.pop_start() == ENTRY_C
    assert await redis_list.pop_end() is None


async def test_list_move(redis_list: ari.RedisEntryList):
    await add_entries(redis_list, *ABCD)

    assert not await redis_list.move("doesn't exist", 0, ari.Whence.ABSOLUTE)
    assert not await redis_list.move(ENTRY_D, 50000, ari.Whence.ABSOLUTE)

    assert await redis_list.move(ENTRY_D, 0, ari.Whence.ABSOLUTE)
    # [d, a, b, c]
    assert await redis_list[0] == ENTRY_D

    assert await redis_list.move(ENTRY_D.aid, 3, ari.Whence.AFTER)
    # [a, b, c, d]
    assert await redis_list.pop_end() == ENTRY_D
    # [a, b, c]

    assert await redis_list.move(ENTRY_B, 2, ari.Whence.BEFORE)
    # [a, b, c]
    assert await redis_list[1:] == [ENTRY_B, ENTRY_C]

    assert await redis_list.move(ENTRY_B.aid, 0, ari.Whence.BEFORE)
    # [b, a, c]
    assert await redis_list[:] == [ENTRY_B, ENTRY_A, ENTRY_C]


async def run_shuffle(l: ari.RedisEntryList,
                      permutations: Set[Tuple[ari.Entry, ...]],
                      max_shuffles: int) -> Optional[int]:
    for i in range(max_shuffles):
        await l.shuffle()
        current = tuple(await l[:])
        permutations.discard(current)

        if not permutations:
            print(f"found all permutations after {i + 1} shuffles")
            return i

    return None


async def test_list_shuffle(redis_list: ari.RedisEntryList):
    # make sure an empty list doesn't cause issues
    await redis_list.shuffle()

    await add_entries(redis_list, *ABCD)

    # test seeding
    seed = 42

    await redis_list.shuffle(seed=seed)
    assert await redis_list[:] == [ENTRY_D, ENTRY_A, ENTRY_B, ENTRY_C]
    await redis_list.shuffle(seed=seed)
    assert await redis_list[:] == [ENTRY_C, ENTRY_D, ENTRY_A, ENTRY_B]


async def test_list_shuffle_permutations(redis_list: ari.RedisEntryList):
    await add_entries(redis_list, *create_entries("abcde"))

    # test if the Fisher-Yates implementation reaches all possible permutations
    permutations = set(itertools.permutations(await redis_list[:]))

    async def permutations_searcher():
        while permutations:
            await redis_list.shuffle()
            order = tuple(await redis_list[:])
            permutations.discard(order)

    # if it takes more than 15 seconds to find all 125 permutations we can be
    # sure that something is wrong. Time is so much easier to reason with than,
    # say, using the distribution to calculate the likelihood of the outcome...
    try:
        await asyncio.wait_for(permutations_searcher(), timeout=15)
    except asyncio.TimeoutError:
        permutations_str = ", ".join(sorted("".join(e.aid for e in p) for p in permutations))
        print(f"missing {len(permutations)} permutations:\n{permutations_str}")
        raise
