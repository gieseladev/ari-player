import dataclasses

__all__ = ["ElakshiTrack"]


@dataclasses.dataclass(frozen=True)
class ElakshiTrack:
    eid: str
