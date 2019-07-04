from __future__ import annotations

import weakref

import aioredis
import andesite
from andesite import AbstractPlayerState, AndesiteEvent, PlayerUpdate, VoiceServerUpdate

import ari
from .manager import PlayerManagerABC

__all__ = ["PlayerManager"]


class PlayerManager(PlayerManagerABC, andesite.AbstractAndesiteState):
    __slots__ = ("_redis", "_manager_key", "_andesite_ws")

    _redis: aioredis.Redis
    _manager_key: str
    _andesite_ws: andesite.AndesiteWebSocketInterface

    _players: weakref.WeakValueDictionary

    def __init__(self, redis: aioredis.Redis, manager_key: str,
                 andesite_ws: andesite.AndesiteWebSocketInterface) -> None:
        self._redis = redis
        self._manager_key = manager_key
        self._andesite_ws = andesite_ws
        andesite_ws.state = self

        self._players = weakref.WeakValueDictionary()

    def get_player(self, guild_id: int) -> ari.PlayerABC:
        try:
            return self._players[guild_id]
        except KeyError:
            player = ari.RedisPlayer(self, self._redis, f"{self._manager_key}:{guild_id}", self._andesite_ws, guild_id)
            self._players[guild_id] = player
            return player

    async def get_track_info(self, eid: str) -> None:
        raise NotImplementedError

    async def get_lp_track(self, eid: str) -> str:
        raise NotImplementedError

    async def handle_player_update(self, update: PlayerUpdate) -> None:
        raise NotImplementedError

    async def handle_andesite_event(self, event: AndesiteEvent) -> None:
        raise NotImplementedError

    async def handle_voice_server_update(self, guild_id: int, update: VoiceServerUpdate) -> None:
        raise NotImplementedError

    async def get(self, guild_id: int) -> AbstractPlayerState:
        raise NotImplementedError
