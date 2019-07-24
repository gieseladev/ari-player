import dataclasses
from typing import Any, Dict, Optional, Tuple

import ari


class AriEventMeta(type):
    uri: Optional[str]

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
    entry: ari.Entry
    paused: bool
    progress: float

    def get_args(self) -> Tuple[Any, ...]:
        return self.entry.as_dict(),

    def get_kwargs(self) -> Dict[str, Any]:
        return {
            "paused": self.paused,
            "progress": self.progress,
        }


@dataclasses.dataclass()
class VolumeChange(AriEvent, uri="on_volume_change"):
    old: float
    new: float


@dataclasses.dataclass()
class QueueAdd(AriEvent, uri="on_queue_add"):
    entry: ari.Entry

    def get_args(self) -> Tuple[Any, ...]:
        return self.entry.as_dict(),