from __future__ import annotations

import abc

import ari


class PlayerManagerABC(abc.ABC):
    __slots__ = ()

    @abc.abstractmethod
    def get_player(self, guild_id: ari.SnowflakeType) -> ari.PlayerABC:
        ...

    @abc.abstractmethod
    async def get_track_info(self, eid: str) -> ari.ElakshiTrack:
        ...
