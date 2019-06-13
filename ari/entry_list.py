"""Queue system."""

import abc
from typing import Optional

import aioredis

__all__ = ["EntryListABC", "RedisEntryList"]


class EntryListABC(abc.ABC):
    """Entry list for keeping track of entries."""

    @abc.abstractmethod
    async def get_length(self) -> int:
        """Get the length of the entry list.

        Returns:
            Length of the entry list.
        """
        ...

    @abc.abstractmethod
    async def get(self, index: int) -> Optional[str]:
        """Get the entry at the given index.

        Args:
            index: Index of the entry to get.

        Returns:
            Entry at the given index or `None` if no entry
            exists at the given index.
        """
        ...

    @abc.abstractmethod
    async def move(self, from_index: int, to_index: int) -> bool:
        """Move an entry in the list.

        Args:
            from_index: Index to move the entry from.
            to_index: Index to move the entry to.

        Returns:
            Whether or not the move succeeded.
        """
        ...

    @abc.abstractmethod
    async def add_front(self, entry: str) -> None:
        """Add an entry to the front of the list.

        Args:
            entry: Entry to add.
        """
        ...

    @abc.abstractmethod
    async def add_end(self, entry: str) -> None:
        """Add an entry to the end of the list.

        Args:
            entry: Entry to add.
        """
        ...

    @abc.abstractmethod
    async def clear(self) -> None:
        """Clear the entry list."""
        ...

    @abc.abstractmethod
    async def shuffle(self) -> None:
        """Shuffle the entry list."""
        ...


class RedisEntryList(EntryListABC):
    """Entry list which uses redis to store the list."""

    _redis: aioredis.Redis
    _list_key: str

    def __init__(self, redis: aioredis.Redis, queue_key: str) -> None:
        self._redis = redis
        self._list_key = queue_key

    async def get_length(self) -> int:
        return await self._redis.llen(self._list_key)

    async def get(self, index: int) -> Optional[str]:
        return await self._redis.lindex(self._list_key, index)

    async def add_end(self, entry: str) -> None:
        await self._redis.rpush(self._list_key, entry)

    async def clear(self) -> None:
        await self._redis.delete(self._list_key)
