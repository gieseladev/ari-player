from __future__ import annotations

import asyncio
import json
import logging
import lptrack
from typing import Any, Callable, Optional, Awaitable

import aiobservable
import aioredis
import andesite

import ari
from ari import events
from ari.entry.redis import maybe_decode_entry
from .player import PlayerABC

__all__ = ["RedisPlayer"]

log = logging.getLogger(__name__)


class RedisPlayer(PlayerABC, andesite.AbstractPlayerState):
    """Player using Redis."""

    __slots__ = ("loop",
                 "_manager",
                 "_redis", "_player_key",
                 "_andesite_ws", "_guild_id",
                 "_queue", "_history")

    loop: Optional[asyncio.AbstractEventLoop]

    _manager: ari.PlayerManagerABC
    _redis: aioredis.Redis
    _player_key: str
    _andesite_ws: andesite.WebSocketInterface
    _guild_id: int

    _queue: ari.RedisEntryList
    _history: ari.RedisEntryList

    _observable: aiobservable.Observable

    def __init__(self, m: ari.PlayerManagerABC,
                 redis: aioredis.Redis, player_key: str,
                 andesite_ws: andesite.WebSocketInterface,
                 guild_id: int, *, loop: asyncio.AbstractEventLoop = None) -> None:
        self.loop = loop

        self._manager = m
        self._redis = redis
        self._player_key = player_key
        self._andesite_ws = andesite_ws
        self._guild_id = guild_id

        self._queue = ari.RedisEntryList(redis, f"{player_key}:queue")
        self._history = ari.RedisEntryList(redis, f"{player_key}:history")

        self._observable = aiobservable.Observable(loop=loop)

    @property
    def observable(self) -> aiobservable.Observable:
        return self._observable

    @property
    def guild_id(self) -> int:
        return self._guild_id

    @property
    def queue(self) -> ari.EntryListABC:
        return self._queue

    @property
    def history(self) -> ari.EntryListABC:
        return self._history

    def _emit(self, event: events.AriEvent) -> Awaitable[None]:
        """Emit an event and attach the guild id to it"""
        event.guild_id = self._guild_id
        return self._observable.emit(event)

    async def connected(self) -> bool:
        return await self._redis.get(f"{self._player_key}:connected") == b"1"

    async def on_connect(self, channel_id: int) -> None:
        await self._redis.set(f"{self._player_key}:connected", b"1")
        await self._update()

    async def on_disconnect(self) -> None:
        await self._redis.set(f"{self._player_key}:connected", b"0")
        await self.pause(True)

    async def get_volume(self) -> float:
        player = await self._get_player()
        return player.volume

    async def set_volume(self, value: float) -> None:
        old_volume = await self.get_volume()
        await self._andesite_ws.volume(self.guild_id, value)

        _ = self._emit(events.VolumeChange(old_volume, value))

    async def get_position(self) -> Optional[float]:
        player = await self._get_player()

        return player.live_position

    async def get_current(self) -> Optional[ari.Entry]:
        return maybe_decode_entry(await self._redis.get(f"{self._player_key}:current", encoding="utf-8"))

    async def pause(self, pause: bool) -> None:
        await self._andesite_ws.pause(self.guild_id, pause)
        # TODO event

    async def paused(self) -> bool:
        player = await self._get_player()
        return player.paused

    async def stop(self) -> None:
        # TODO what does "stop" mean?
        await self._andesite_ws.stop(self.guild_id)
        # TODO event

    async def seek(self, position: float) -> None:
        await self._andesite_ws.seek(self.guild_id, position)
        # TODO event

    async def _update(self) -> None:
        # TODO this isn't a good check
        connected, paused, current_entry = await asyncio.gather(self.connected(),
                                                                self.paused(),
                                                                self.get_current(), loop=self.loop)
        if connected and not current_entry and not paused:
            await self.next()

    async def _play(self, entry: Optional[ari.Entry]) -> None:
        if entry is None:
            await self.stop()
            return

        track = await self._get_lp_track(entry.eid)
        await self._andesite_ws.play(self.guild_id, track)

    async def next(self) -> None:
        entry = await self._queue.pop_start()
        await self._play(entry)
        # TODO event

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

        # TODO
        raise NotImplementedError
        # TODO event

    async def previous(self) -> None:
        entry = await self._history.pop_start()

        current = await self.get_current()
        if current is not None:
            await self._queue.add_start(current)

        await self._play(entry)
        # TODO event

    async def previous_chapter(self) -> None:
        info = await self._get_current_track_info()
        if info is None:
            await self.previous()
        else:
            pass

        # TODO
        raise NotImplementedError
        # TODO event

    async def enqueue(self, entry: ari.Entry) -> None:
        await self._queue.add_end(entry)
        await self._update()
        # TODO event

    async def _get_player(self) -> andesite.Player:
        """Get the player for sure.

        If no player currently exists, get it from Andesite directly.
        """
        player = await self.get_player()
        if player is None:
            log.info("guild %s doesn't have a player, getting from Andesite", self.guild_id)
            player = await self._andesite_ws.get_player(self.guild_id)

        return player

    async def get_player(self) -> Optional[andesite.Player]:
        return await get_optional_transform(
            self._redis,
            f"{self._player_key}:andesite:player",
            andesite.player_from_raw,
        )

    async def set_player(self, player: Optional[andesite.Player]) -> None:
        await set_optional_transform(
            self._redis, player,
            f"{self._player_key}:andesite:player",
            andesite.player_to_raw
        )

    async def get_voice_server_update(self) -> Optional[andesite.VoiceServerUpdate]:
        return await get_optional_transform(
            self._redis,
            f"{self._player_key}:andesite:voice",
            andesite.voice_server_update_from_raw
        )

    async def set_voice_server_update(self, update: Optional[andesite.VoiceServerUpdate]) -> None:
        await set_optional_transform(
            self._redis, update,
            f"{self._player_key}:andesite:voice",
            andesite.voice_server_update_to_raw
        )

    async def get_track(self) -> Optional[str]:
        return await self._redis.get(f"{self._player_key}:andesite:track", encoding="utf-8")

    async def set_track(self, track: Optional[str]) -> None:
        key = f"{self._player_key}:andesite:track"
        if track is None:
            await self._redis.delete(key)
        else:
            await self._redis.set(key, track)

    async def _get_lp_track(self, eid: str) -> str:
        """Generate the lavaplayer track string for the eid."""

        # elakshi_track = await self._manager.get_track_info(eid)
        # TODO create lp track from elakshi
        lp_track = lptrack.Track(
            version=None,
            source=lptrack.Youtube(),
            info=lptrack.TrackInfo(
                title=eid,
                author="placeholder",
                duration=205.,
                identifier="Pkh8UtuejGw",
                is_stream=False,
                uri="https://www.youtube.com/watch?v=Pkh8UtuejGw",
            ),
        )
        return lptrack.encode(lp_track).decode()


async def get_optional_transform(redis: aioredis.Redis, key: str, transformer: Optional[Callable]) -> Optional[Any]:
    """Get a key from redis.

    If the value of the key isn't `None`, run the json decoded value through
    the transformer.
    """
    ser_data = await redis.get(key)
    if ser_data is None:
        return None

    try:
        raw_data = json.loads(ser_data)

        if transformer:
            return transformer(raw_data)
        else:
            return raw_data
    except Exception:
        log.exception("couldn't decode %s", ser_data)
        return


async def set_optional_transform(redis: aioredis.Redis, data: Optional[Any],
                                 key: str, transformer: Optional[Callable]) -> None:
    """Set a key in redis to the value.

    The value is transformed with the transformer if it isn't `None` and the
    transformer also isn't `None`
    """
    if data is None:
        await redis.delete(key)
        return

    try:
        if transformer:
            raw_data = transformer(data)
        else:
            raw_data = data

        ser_data = json.dumps(raw_data)
    except Exception:
        log.exception("couldn't encode %s", data)
        return

    await redis.set(key, ser_data)
