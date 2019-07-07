import abc
from typing import List, Optional, Union, overload

from .entry import Entry

__all__ = ["EntryListABC", "get_entry_list_page"]


class EntryListABC(abc.ABC):
    """Entry list for keeping track of entries."""

    @abc.abstractmethod
    async def get_length(self) -> int:
        """Get the length of the entry list.

        Returns:
            Length of the entry list.
        """
        ...

    @overload
    async def get(self, index: int) -> Optional[Entry]: ...

    @overload
    async def get(self, index: slice) -> List[Entry]: ...

    @abc.abstractmethod
    async def get(self, index: Union[int, slice]) -> Union[Optional[Entry], List[Entry]]:
        """Get the entry at the given index.

        Args:
            index: Index of the entry to get, or a slice object
                to get a range of entries.

        Returns:
            If given an index, it returns an `Entry` at the given index or
            `None` if no entry exists at the given index.

            In the case of a slice the return value is a list of `Entry`.
        """
        ...

    @abc.abstractmethod
    async def remove(self, entry: Union[Entry, str]) -> bool:
        """Remove an entry from the list.

        Args:
            entry: Entry to remove. Can be an `Entry` or just the aid.

        Returns:
            Whether or not the entry was successfully removed.
        """
        ...

    @abc.abstractmethod
    async def move(self, entry: Union[Entry, str], to_index: int) -> bool:
        """Move an entry in the list.

        Args:
            entry: Entry to move.
            to_index: Index to move the entry to.

        Returns:
            Whether or not the move succeeded.
        """
        ...

    @abc.abstractmethod
    async def add_start(self, entry: Entry) -> None:
        """Add an entry to the front of the list.

        Args:
            entry: Entry to add.
        """
        ...

    @abc.abstractmethod
    async def add_end(self, entry: Entry) -> None:
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

    @abc.abstractmethod
    async def pop_start(self) -> Optional[Entry]:
        """Pop from the start of the list."""
        ...

    @abc.abstractmethod
    async def pop_end(self) -> Optional[Entry]:
        """Pop from the end of the list."""
        ...


async def get_entry_list_page(l: EntryListABC, page: int, entries_per_page: int) -> List[Entry]:
    """Get a page of entries."""
    start = page * entries_per_page
    end = start + entries_per_page
    return await l.get(slice(start, end))
