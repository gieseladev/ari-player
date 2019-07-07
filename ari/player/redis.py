import json
import logging
from typing import Any, Callable, Optional

import aioredis
import andesite
from andesite import Player, VoiceServerUpdate

import ari
from ari.entry.redis import maybe_decode_entry
from .player import PlayerABC

__all__ = ["RedisPlayer"]

log = logging.getLogger(__name__)


class RedisPlayer(PlayerABC, andesite.AbstractPlayerState):
    """Player using Redis."""

    __slots__ = ("_manager",
                 "_redis", "_player_key",
                 "_andesite_ws", "_guild_id",
                 "_queue", "_history")

    _manager: ari.PlayerManagerABC
    _redis: aioredis.Redis
    _player_key: str
    _andesite_ws: andesite.AndesiteWebSocketInterface
    _guild_id: int

    _queue: ari.RedisEntryList
    _history: ari.RedisEntryList

    def __init__(self, m: ari.PlayerManagerABC,
                 redis: aioredis.Redis, player_key: str,
                 andesite_ws: andesite.AndesiteWebSocketInterface,
                 guild_id: int) -> None:
        self._manager = m
        self._redis = redis
        self._player_key = player_key
        self._andesite_ws = andesite_ws
        self._guild_id = guild_id

        self._queue = ari.RedisEntryList(redis, f"{player_key}:queue")
        self._history = ari.RedisEntryList(redis, f"{player_key}:history")

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def queue(self) -> ari.EntryListABC:
        return self._queue

    @property
    def history(self) -> ari.EntryListABC:
        return self._history

    async def get_volume(self) -> float:
        player = await self.get_player()
        if player is None:
            player = await self._andesite_ws.get_player(self.guild_id)

        return player.volume

    async def get_position(self) -> Optional[float]:
        player = await self.get_player()
        if player is None:
            return None

        return player.live_position

    async def set_volume(self, value: float) -> None:
        await self._andesite_ws.volume(self.guild_id, value)

    async def get_current(self) -> Optional[ari.Entry]:
        return maybe_decode_entry(await self._redis.get(f"{self._player_key}:current"))

    async def pause(self, pause: bool) -> None:
        await self._andesite_ws.pause(self.guild_id, pause)

    async def stop(self) -> None:
        await self._andesite_ws.stop(self.guild_id)

    async def seek(self, position: float) -> None:
        await self._andesite_ws.seek(self.guild_id, position)

    async def _play(self, entry: Optional[ari.Entry]) -> None:
        if entry is None:
            await self.stop()
            return

        raise NotImplementedError
        track = await self._manager.get_lp_track(entry.eid)
        await self._andesite_ws.play(self.guild_id, track)

    async def next(self) -> None:
        entry = await self.queue.pop_start()
        await self._play(entry)

    async def _get_current_track_info(self) -> Optional[ari.ElakshiTrack]:
        entry = await self.get_current()
        if entry is None:
            return None
        else:
            return await self._manager.get_track_info(entry.eid)

    async def next_chapter(self) -> None:
        info = await self._get_current_track_info()
        if info is None:
            await self.next()
        else:
            pass

        raise NotImplementedError

    async def previous(self) -> None:
        entry = await self.history.pop_start()

        current = await self.get_current()
        if current is not None:
            await self.queue.add_start(current)

        await self._play(entry)

    async def previous_chapter(self) -> None:
        info = await self._get_current_track_info()
        if info is None:
            await self.previous()
        else:
            pass

        raise NotImplementedError

    async def get_player(self) -> Optional[Player]:
        return await get_optional_transform(
            self._redis,
            f"{self._player_key}:current:andesite:player",
            andesite.player_from_raw,
        )

    async def set_player(self, player: Optional[Player]) -> None:
        await set_optional_transform(
            self._redis, player,
            f"{self._player_key}:current:andesite:player",
            andesite.player_to_raw
        )

    async def get_voice_server_update(self) -> Optional[VoiceServerUpdate]:
        return await get_optional_transform(
            self._redis,
            f"{self._player_key}:current:andesite:voice",
            andesite.voice_server_update_from_raw
        )

    async def set_voice_server_update(self, update: Optional[VoiceServerUpdate]) -> None:
        await set_optional_transform(
            self._redis, update,
            f"{self._player_key}:current:andesite:voice",
            andesite.voice_server_update_to_raw
        )

    async def get_track(self) -> Optional[str]:
        return await self._redis.get(f"{self._player_key}:current:andesite:track")

    async def set_track(self, track: Optional[str]) -> None:
        key = f"{self._player_key}:current:andesite:track"
        if track is None:
            await self._redis.delete(key)
        else:
            await self._redis.set(key, track)


async def get_optional_transform(redis: aioredis.Redis, key: str, transformer: Optional[Callable]) -> Optional[Any]:
    ser_data = await redis.get(key)
    if ser_data == "":
        return None

    try:
        raw_data = json.loads(ser_data)

        if transformer:
            return transformer(raw_data)
        else:
            return raw_data
    except Exception as e:
        log.warning("couldn't decode %s: %s", ser_data, e)
        return


async def set_optional_transform(redis: aioredis.Redis, data: Optional[Any],
                                 key: str, transformer: Optional[Callable]) -> None:
    if data is None:
        await redis.delete(key)
        return

    try:
        if transformer:
            raw_data = transformer(data)
        else:
            raw_data = data

        ser_data = json.dumps(raw_data)
    except Exception as e:
        log.warning("couldn't encode %s: %s", data, e)
        return

    await redis.set(key, ser_data)
