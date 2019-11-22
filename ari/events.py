import dataclasses
from typing import Any, Dict, Optional, Tuple

import ari


class AriEventMeta(type):
    def __new__(mcs, *args, uri: Optional[str]) -> type:
        cls = type.__new__(mcs, *args)
        cls.uri = uri
        return cls


class AriEvent(metaclass=AriEventMeta, uri=None):
    uri: Optional[str]

    guild_id: Optional[int]

    def get_args(self) -> Tuple[Any, ...]:
        args = dataclasses.astuple(self)

        if self.guild_id is not None:
            return (self.guild_id, *args)
        else:
            return args

    def get_kwargs(self) -> Dict[str, Any]:
        return {}


@dataclasses.dataclass()
class Play(AriEvent, uri="on_play"):
    entry: Optional[ari.Entry]
    paused: bool
    position: Optional[float]

    def get_args(self) -> Tuple[Any, ...]:
        entry = self.entry.as_dict() if self.entry else None
        return self.guild_id, entry,

    def get_kwargs(self) -> Dict[str, Any]:
        return {
            "paused": self.paused,
            "position": self.position,
        }


@dataclasses.dataclass()
class Stop(AriEvent, uri="on_stop"):
    ...


@dataclasses.dataclass()
class VolumeChange(AriEvent, uri="on_volume_change"):
    old: float
    new: float


@dataclasses.dataclass()
class _EntryBase(AriEvent, uri=None):
    entry: ari.Entry

    def get_args(self) -> Tuple[Any, ...]:
        return self.guild_id, self.entry.as_dict(),


@dataclasses.dataclass()
class QueueAdd(_EntryBase, uri="on_queue_add"):
    ...


@dataclasses.dataclass()
class QueueRemove(_EntryBase, uri="on_queue_remove"):
    ...


@dataclasses.dataclass()
class HistoryAdd(_EntryBase, uri="on_history_add"):
    ...


@dataclasses.dataclass()
class HistoryRemove(_EntryBase, uri="on_history_remove"):
    ...
