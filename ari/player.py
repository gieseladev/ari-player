"""Ari players."""

import abc
from typing import Optional

import aioredis
from andesite import Player

from .entry_list import EntryListABC, RedisEntryList

__all__ = ["PlayerABC", "Player"]


# TODO: volume
class PlayerABC(abc.ABC):
    """Ari player."""

    @property
    @abc.abstractmethod
    def guild_id(self) -> int:
        """Guild id the player is for."""
        ...

    @property
    @abc.abstractmethod
    def queue(self) -> EntryListABC:
        """Queued entry list."""
        ...

    @property
    @abc.abstractmethod
    def history(self) -> EntryListABC:
        """Past entry list."""
        ...

    @abc.abstractmethod
    async def get_current(self) -> Optional[str]:
        """Get the current entry."""
        ...

    @abc.abstractmethod
    async def pause(self, pause: bool) -> None:
        """Pause the current entry."""
        ...

    @abc.abstractmethod
    async def stop(self) -> None:
        """Stop the player.

        This is basically `next` and `pause`.
        """
        ...

    @abc.abstractmethod
    async def seek(self, position: float) -> None:
        """Seek the current song to the given position."""
        ...

    @abc.abstractmethod
    async def next(self) -> None:
        """Play the next entry from the queue."""
        ...

    @abc.abstractmethod
    async def next_chapter(self) -> None:
        """Play the next chapter from the current entry.

        If the current entry doesn't have a next chapter, play the next entry.
        """
        ...

    @abc.abstractmethod
    async def previous(self) -> None:
        """Play the previous entry from the history."""
        ...

    @abc.abstractmethod
    async def previous_chapter(self) -> None:
        """Play the previous chapter from the current entry.

        If the current entry doesn't have a previous chapter, play the previous
        entry.
        """
        ...


class RedisPlayer(PlayerABC):
    """Player using Redis."""

    _redis: aioredis.Redis
    _player_key: str

    _guild_id: int
    _queue: RedisEntryList
    _history: RedisEntryList

    def __init__(self, redis: aioredis.Redis, player_key: str, guild_id: int) -> None:
        self._redis = redis
        self._player_key = player_key

        self._guild_id = guild_id
        self._queue = RedisEntryList(redis, f"{player_key}:queue")
        self._history = RedisEntryList(redis, f"{player_key}:history")

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def queue(self) -> EntryListABC:
        return self._queue

    @property
    def history(self) -> EntryListABC:
        return self._history

    async def get_current(self) -> Optional[str]:
        pass
