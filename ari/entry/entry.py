import uuid
from typing import Dict

__all__ = ["Entry", "new_aid"]


class Entry:
    """Entry.

    Attributes:
        aid (str): Ari entry id.
        eid (str): Elakshi track id.
    """

    __slots__ = ("aid", "eid")

    aid: str
    eid: str

    def __init__(self, aid: str, eid: str) -> None:
        self.aid = aid
        self.eid = eid

    def __repr__(self) -> str:
        return f"Entry({self.aid!r}, {self.eid!r})"

    def __str__(self) -> str:
        return f"EID({self.eid}) #{self.aid}"

    def __hash__(self) -> int:
        return hash(self.aid)

    def as_dict(self) -> Dict[str, str]:
        return {"aid": self.aid, "eid": self.eid}


def new_aid() -> str:
    """Create a new, unique ari entry id."""
    return uuid.uuid4().hex