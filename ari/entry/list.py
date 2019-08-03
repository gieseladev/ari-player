import abc
import enum
from typing import List, Optional, Union, overload

from .entry import Entry

__all__ = ["EntryListABC",
           "Whence", "MutEntryListABC",
           "get_entry_list_page"]


# TODO enable capped list

class EntryListABC(abc.ABC):
    """Read-only sequence of entries."""
    __slots__ = ()

    def __getitem__(self, index: Union[int, str, slice]):
        return self.get(index)

    @abc.abstractmethod
    async def get_length(self) -> int:
        """Get the length of the entry list.

        Returns:
            Amount of entries currently in the list.
        """
        ...

    @overload
    async def get(self, index: int) -> Optional[Entry]: ...

    @overload
    async def get(self, index: str) -> Optional[Entry]: ...

    @overload
    async def get(self, index: slice) -> List[Entry]: ...

    @abc.abstractmethod
    async def get(self, index: Union[int, str, slice]) -> Union[Optional[Entry], List[Entry]]:
        """Get the entry at the given index.

        Args:
            index: One of the following:

                - Index of the entry
                - AID of the entry
                - Slice object to get a range of entries.

        Returns:
            If given an index, it returns the entry at the given index or
            `None` if the index is out of bounds.

            In the case of a slice the return value is a list of `Entry`.
        """
        ...


class Whence(enum.Enum):
    """How a position is to be interpreted."""
    ABSOLUTE = "absolute"
    BEFORE = "before"
    AFTER = "after"


class MutEntryListABC(EntryListABC, abc.ABC):
    """Mutable sequence of entries."""
    __slots__ = ()

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
    async def move(self, entry: Union[Entry, str], index: int, whence: Whence) -> bool:
        """Move an entry in the list.

        Args:
            entry: Entry to move.
            index: Index to move the entry to.
            whence: How to interpret the given index.

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
    """Get a page of entries.

    Args:
        l: Entry list to get the page from
        page: Page index to get.
        entries_per_page: The amount of entries per page

    Returns:
        A list of entries which are on the given page.
    """
    start = page * entries_per_page
    end = start + entries_per_page
    return await l.get(slice(start, end))
