from __future__ import annotations

import asyncio
import logging
import marshal
from typing import Any, Awaitable, Callable, Optional, Union

import aiobservable
import aioredis
import andesite
import lptrack

import ari
from ari import events
from .player import PlayerABC

__all__ = ["RedisPlayer"]

log = logging.getLogger(__name__)

DEFAULT = object()


class RedisAndesitePlayerState(andesite.AbstractPlayerState):
    __slots__ = ("__guild_id",
                 "_redis", "_key")

    __guild_id: int

    _redis: aioredis.Redis
    _key: str

    def __init__(self, guild_id: int, redis: aioredis.Redis, key: str) -> None:
        self.__guild_id = guild_id
        self._redis = redis
        self._key = key

    @property
    def guild_id(self) -> int:
        return self.__guild_id

    async def get_player(self) -> Optional[andesite.Player]:
        return await get_optional_transform(
            self._redis,
            f"{self._key}:player",
            andesite.player_from_raw,
        )

    async def set_player(self, player: Optional[andesite.Player]) -> None:
        await set_optional_transform(
            self._redis, player,
            f"{self._key}:player",
            andesite.player_to_raw,
        )

    async def get_voice_server_update(self) -> Optional[andesite.VoiceServerUpdate]:
        return await get_optional_transform(
            self._redis,
            f"{self._key}:voice",
            andesite.voice_server_update_from_raw,
        )

    async def set_voice_server_update(self, update: Optional[andesite.VoiceServerUpdate]) -> None:
        await set_optional_transform(
            self._redis, update,
            f"{self._key}:voice",
            andesite.voice_server_update_to_raw,
        )

    async def get_track(self) -> Optional[str]:
        return await self._redis.get(f"{self._key}:track", encoding="utf-8")

    async def set_track(self, track: Optional[str]) -> None:
        key = f"{self._key}:track"
        if track is None:
            await self._redis.delete(key)
        else:
            await self._redis.set(key, track)


class RedisPlayer(PlayerABC):
    """Player using Redis."""
    __slots__ = ("_manager",
                 "_redis", "_player_key", "_guild_id",
                 "_andesite_ws", "_andesite_state",
                 "_queue", "_history",
                 "_observable",
                 "__weakref__")

    _manager: ari.PlayerManagerABC
    _redis: aioredis.Redis
    _player_key: str
    _guild_id: int

    _andesite_ws: andesite.WebSocketInterface
    _andesite_state: RedisAndesitePlayerState

    _queue: ari.RedisEntryList
    _history: ari.RedisEntryList

    _observable: aiobservable.Observable

    def __init__(self, m: ari.PlayerManagerABC,
                 redis: aioredis.Redis, player_key: str,
                 andesite_ws: andesite.WebSocketInterface,
                 guild_id: ari.SnowflakeType) -> None:
        self._manager = m
        self._redis = redis
        self._player_key = player_key
        self._guild_id = int(guild_id)

        self._andesite_ws = andesite_ws
        self._andesite_state = RedisAndesitePlayerState(self._guild_id, redis, f"{player_key}:andesite")

        self._queue = ari.RedisEntryList(redis, f"{player_key}:queue")
        self._history = ari.RedisEntryList(redis, f"{player_key}:history")

        self._observable = aiobservable.Observable()

    def __str__(self) -> str:
        return f"RedisPlayer(guild_id={self._guild_id})"

    @property
    def observable(self) -> aiobservable.Observable:
        return self._observable

    @property
    def guild_id(self) -> str:
        return str(self._guild_id)

    @property
    def queue(self) -> ari.EntryListABC:
        return self._queue

    @property
    def history(self) -> ari.EntryListABC:
        return self._history

    @property
    def andesite_state(self) -> andesite.AbstractPlayerState:
        """Andesite state handler."""
        return self._andesite_state

    def __emit(self, event: events.AriEvent) -> Awaitable[None]:
        """Emit an event and attach the guild id to it"""
        event.guild_id = self._guild_id
        return self._observable.emit(event)

    async def __emit_play(self, *,
                          entry: ari.Entry = DEFAULT,
                          paused: bool = DEFAULT,
                          position: float = DEFAULT) -> None:
        data = {}

        async def setter(key: str, value: Union[Any, DEFAULT], corof: Callable[[], Awaitable[Any]]) -> None:
            nonlocal data

            if value is DEFAULT:
                value = await corof()

            data[key] = value

        await asyncio.gather(
            setter("entry", entry, self.get_current),
            setter("paused", paused, self.paused),
            setter("position", position, self.get_position),
        )

        await self.__emit(events.Play(**data))

    async def connected(self) -> bool:
        return await self._redis.get(f"{self._player_key}:connected") == b"1"

    async def on_connect(self, channel_id: str) -> None:
        log.debug("%s connected to %s", self, channel_id)
        await self._redis.set(f"{self._player_key}:connected", b"1")
        await self._update(resume=True)

    async def on_disconnect(self) -> None:
        log.debug("%s disconnected", self)

        await self._redis.delete(f"{self._player_key}:connected")
        await self.pause(True)

    async def on_track_end(self, event: andesite.TrackEndEvent) -> None:
        log.debug("%s track ended", event)

        current = await self.get_current()
        if current is not None:
            log.debug("%s: adding current entry to history: %s", self, current)
            await self._history.add_start(current)
            await self.__emit(events.HistoryAdd(current))
        else:
            log.warning("%s: no current entry when track ended: %s", self, event)

        if event.may_start_next:
            await self.next()

    async def get_volume(self) -> float:
        player = await self._get_player()
        if player is None:
            return 1

        return player.volume

    async def set_volume(self, value: float) -> None:
        log.debug("%s setting volume to %s", self, value)

        old_volume = await self.get_volume()
        await self._andesite_ws.volume(self._guild_id, value)

        await self.__emit(events.VolumeChange(old_volume, value))

    async def get_position(self) -> Optional[float]:
        player = await self._get_player()
        if player is None:
            return None

        return player.live_position

    async def get_current(self) -> Optional[ari.Entry]:
        raw = await self._redis.get(f"{self._player_key}:current")
        if raw:
            return ari.Entry.from_dict(marshal.loads(raw))
        else:
            return None

    async def pause(self, pause: bool) -> None:
        log.debug("%s (un)pausing pause=%s", self, pause)
        await self._andesite_ws.pause(self._guild_id, pause)

        await self.__emit_play(paused=pause)

    async def paused(self) -> bool:
        player = await self._get_player()
        if player is None:
            return False

        return player.paused

    async def stop(self) -> None:
        log.debug("%s stopping", self)
        await asyncio.gather(
            self._andesite_ws.stop(self._guild_id),
            self._queue.clear(),
        )

        await self.__emit(events.Stop())

    async def seek(self, position: float) -> None:
        log.debug("%s seeking to %s", self, position)
        await self._andesite_ws.seek(self._guild_id, position)

        await self.__emit_play(position=position)

    async def _update(self, *, resume: bool = False) -> None:
        log.debug("%s updating self (resume=%s)", self, resume)
        connected, paused, current_entry = await asyncio.gather(
            self.connected(),
            self.paused(),
            self.get_current(),
        )

        if resume and connected and paused:
            await self.pause(False)
        elif connected and not current_entry and not paused:
            await self.next()
        else:
            log.debug("%s no need to update", self)

    async def _play(self, entry: Optional[ari.Entry]) -> None:
        if entry is None:
            await self._andesite_ws.stop(self._guild_id)
            await self._redis.delete(f"{self._player_key}:current")
        else:
            track = await self._get_lp_track(entry.eid)
            await self._andesite_ws.play(self._guild_id, track)

            raw_enty = marshal.dumps(entry.as_dict())
            await self._redis.set(f"{self._player_key}:current", raw_enty)

        await self.__emit_play(entry=entry)

    async def next(self) -> None:
        log.debug("%s playing next", self)
        entry = await self._queue.pop_start()
        await self.__emit(events.QueueRemove(entry))
        await self._play(entry)

    async def _get_current_track_info(self) -> Optional[ari.ElakshiTrack]:
        entry = await self.get_current()
        if entry is None:
            return None
        else:
            return await self._manager.get_track_info(entry.eid)

    async def next_chapter(self) -> None:
        log.debug("%s seeking to next chapter", self)
        info = await self._get_current_track_info()
        if info is None:
            await self.next()
        else:
            pass

        # TODO
        raise NotImplementedError
        # TODO event for chapter skip

    async def previous(self) -> None:
        log.debug("%s playing previous entry", self)
        entry = await self._history.pop_start()
        await self.__emit(events.HistoryRemove(entry))

        current = await self.get_current()
        if current is not None:
            await self._queue.add_start(current)
            # TODO queue event position?
            await self.__emit(events.QueueAdd(current))

        await self._play(entry)

    async def previous_chapter(self) -> None:
        log.debug("%s seeking to previous chapter", self)
        info = await self._get_current_track_info()
        if info is None:
            await self.previous()
        else:
            pass

        # TODO
        raise NotImplementedError
        # TODO event for chapter skip

    async def enqueue(self, entry: ari.Entry) -> None:
        log.debug("%s adding entry to the queue: %s", self, entry)
        await self._queue.add_end(entry)
        await self.__emit(events.QueueAdd(entry))

        await self._update()

    async def dequeue(self, entry: Union[ari.Entry, str]) -> bool:
        return await self._queue.remove(entry)

    async def move(self, entry: Union[ari.Entry, str], index: int, whence: ari.Whence) -> bool:
        return await self._queue.move(entry, index, whence)

    async def _get_player(self) -> Optional[andesite.Player]:
        """Get the player for sure.

        If no player currently exists, get it from Andesite directly.
        If Andesite doesn't return a player, `None` is returned.
        """
        player = await self._andesite_state.get_player()
        if player is None:
            log.info("guild %s doesn't have a player state stored, asking Andesite", self._guild_id)
            player = await self._andesite_ws.get_player(self._guild_id)

        return player

    async def _get_lp_track(self, eid: str) -> str:
        """Generate the LavaPlayer track string for the eid."""
        audio_source = await self._manager.get_audio_source(eid)

        lp_track = lptrack.Track(
            version=None,
            source=lptrack.get_source(audio_source.source)(),
            info=lptrack.TrackInfo(
                title=f"Track {eid}",
                author="Elakshi",
                duration=audio_source.end_offset - audio_source.start_offset,
                identifier=audio_source.identifier,
                is_stream=audio_source.is_live,
                # TODO use proper uri!
                uri=f"https://www.youtube.com/watch?v={audio_source.identifier}",
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
        raw_data = marshal.loads(ser_data)

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

        ser_data = marshal.dumps(raw_data)
    except Exception:
        log.exception("couldn't encode %s", data)
        return

    await redis.set(key, ser_data)
