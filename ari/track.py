import dataclasses

__all__ = ["ElakshiTrack", "AudioSource"]


@dataclasses.dataclass(frozen=True)
class ElakshiTrack:
    eid: str


@dataclasses.dataclass(frozen=True)
class AudioSource:
    source: str
    identifier: str
    uri: str
    start_offset: float
    end_offset: float
    is_live: bool
