import abc
from typing import Optional

import ari

__all__ = ["PlayerABC"]


class PlayerABC(abc.ABC):
    """Ari player."""

    @property
    @abc.abstractmethod
    def guild_id(self) -> int:
        """Guild id the player is for."""
        ...

    @property
    @abc.abstractmethod
    def queue(self) -> ari.EntryListABC:
        """Queued entry list."""
        ...

    @property
    @abc.abstractmethod
    def history(self) -> ari.EntryListABC:
        """Past entry list."""
        ...

    @abc.abstractmethod
    async def get_current(self) -> Optional[ari.Entry]:
        """Get the current entry."""
        ...

    @abc.abstractmethod
    async def get_position(self) -> Optional[float]:
        """Get the position in seconds."""
        ...

    @abc.abstractmethod
    async def get_volume(self) -> float:
        """Get the volume as a percentage."""
        ...

    @abc.abstractmethod
    async def set_volume(self, value: float) -> None:
        """Set the volume."""
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
        """Seek the current song to the given position.

        If the position is outside the range of the current track, skip
        to the next entry.
        """
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
