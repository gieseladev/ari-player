import uuid
from typing import Any, Dict

__all__ = ["Entry", "new_aid"]


class Entry:
    """Track entry data."""

    __slots__ = ("aid", "eid",
                 "meta")

    aid: str
    """Ari entry id."""
    eid: str
    """Elakshi track id."""

    meta: Dict[str, Any]
    """Metadata for the entry."""

    def __init__(self, aid: str, eid: str, meta: Dict[str, Any] = None) -> None:
        self.aid = aid
        self.eid = eid
        self.meta = meta or {}

    def __repr__(self) -> str:
        return f"Entry({self.aid!r}, {self.eid!r})"

    def __str__(self) -> str:
        return f"EID({self.eid}) #{self.aid}"

    def __hash__(self) -> int:
        return hash(self.aid)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Entry):
            return self.aid == other.aid
        else:
            return NotImplemented

    @classmethod
    def from_dict(cls, data: Dict[str, str]):
        return Entry(data["aid"], data["eid"], data.get("meta"))

    def as_dict(self) -> Dict[str, str]:
        d = {"aid": self.aid, "eid": self.eid}
        if self.meta:
            d["meta"] = self.meta

        return d


def new_aid() -> str:
    """Create a new, unique ari entry id."""
    return uuid.uuid4().hex
