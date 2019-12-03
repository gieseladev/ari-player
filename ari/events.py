import dataclasses
from typing import Any, ClassVar, Dict, Optional, Tuple

import ari


class AriEventMeta(type):
    __slots__ = ()

    def __new__(mcs, *args, uri: Optional[str]) -> type:
        cls = super().__new__(mcs, *args)
        cls.uri = uri
        return cls


class AriEvent(metaclass=AriEventMeta, uri=None):
    uri: ClassVar[Optional[str]]

    __slots__ = ("guild_id",)

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
class Connect(AriEvent, uri="on_connect"):
    __slots__ = ("channel_id",)

    channel_id: Optional[str]


@dataclasses.dataclass()
class PlayUpdate(AriEvent, uri="on_play_update"):
    __slots__ = ("entry", "paused", "position")

    entry: Optional[ari.Entry]
    paused: bool
    position: Optional[float]

    def get_args(self) -> Tuple[Any, ...]:
        return self.guild_id,

    def get_kwargs(self) -> Dict[str, Any]:
        return {
            "entry": self.entry.as_dict() if self.entry else None,
            "paused": self.paused,
            "position": self.position,
        }


@dataclasses.dataclass()
class Play(AriEvent, uri="on_play"):
    __slots__ = ("entry",)

    entry: Optional[ari.Entry]

    def get_args(self) -> Tuple[Any, ...]:
        entry = self.entry.as_dict() if self.entry else None
        return self.guild_id, entry


@dataclasses.dataclass()
class Pause(AriEvent, uri="on_pause"):
    __slots__ = ("paused",)

    paused: bool


@dataclasses.dataclass()
class Seek(AriEvent, uri="on_seek"):
    __slots__ = ("position",)

    position: float


@dataclasses.dataclass()
class VolumeChange(AriEvent, uri="on_volume_change"):
    __slots__ = ("old", "new")

    old: float
    new: float


@dataclasses.dataclass()
class Stop(AriEvent, uri="on_stop"):
    __slots__ = ()


@dataclasses.dataclass()
class _EntryBase(AriEvent, uri=None):
    __slots__ = ("entry",)

    entry: ari.Entry

    def get_args(self) -> Tuple[Any, ...]:
        return self.guild_id, self.entry.as_dict()


@dataclasses.dataclass()
class QueueAdd(_EntryBase, uri="on_queue_add"):
    __slots__ = ("position",)

    position: int

    def get_kwargs(self) -> Dict[str, Any]:
        d = super().get_kwargs()
        d.update(position=self.position)
        return d


@dataclasses.dataclass()
class QueueRemove(_EntryBase, uri="on_queue_remove"):
    __slots__ = ()


@dataclasses.dataclass()
class QueueMove(_EntryBase, uri="on_queue_move"):
    __slots__ = ("position",)

    position: int

    def get_kwargs(self) -> Dict[str, Any]:
        d = super().get_kwargs()
        d.update(position=self.position)
        return d


@dataclasses.dataclass()
class HistoryAdd(_EntryBase, uri="on_history_add"):
    __slots__ = ()


@dataclasses.dataclass()
class HistoryRemove(_EntryBase, uri="on_history_remove"):
    __slots__ = ()
