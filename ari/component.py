from __future__ import annotations

import dataclasses
import logging
import weakref
from typing import Any, Dict, List, Optional

import aioredis
import andesite
from autobahn.asyncio.component import Component
from autobahn import wamp

import ari
from ari import events

__all__ = ["AriServer", "create_ari_server", "create_component"]

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class VoiceUpdate:
    state_update: Optional[Dict[str, Any]]
    server_update: Optional[Dict[str, str]]

    @property
    def done(self) -> bool:
        return self.state_update is not None and self.server_update is not None

    @property
    def session_id(self) -> str:
        return self.state_update["session_id"]

    @property
    def guild_id(self) -> str:
        return self.server_update["guild_id"]

    @property
    def channel_id(self) -> str:
        return self.state_update["channel_id"]


class AriServer(ari.PlayerManagerABC):
    __slots__ = ("config",
                 "_redis", "_manager_key", "_andesite_ws",
                 "_players",
                 "_session",
                 "_voice_updates")

    config: ari.Config

    _redis: aioredis.Redis
    _manager_key: str
    _andesite_ws: andesite.WebSocketInterface

    _players: weakref.WeakValueDictionary

    _session: Optional[wamp.ISession]

    _voice_updates: Dict[str, VoiceUpdate]

    def __init__(self, config: ari.Config, redis: aioredis.Redis, manager_key: str,
                 andesite_ws: andesite.WebSocketInterface) -> None:
        self.config = config

        self._redis = redis
        self._manager_key = manager_key
        self._andesite_ws = andesite_ws
        andesite_ws.state = andesite.State(state_factory=self.__get_player_state, keep_states=False)
        andesite_ws.event_target.on(andesite.TrackEndEvent, self.on_andesite_track_end)

        self._players = weakref.WeakValueDictionary()

        self._session = None

        self._voice_updates = {}

    def __create_player(self, guild_id: str) -> ari.RedisPlayer:
        player = ari.RedisPlayer(self, self._redis, f"{self._manager_key}:{guild_id}", self._andesite_ws, guild_id)
        player.observable.on(callback=self.on_player_event)
        return player

    def get_player(self, guild_id: ari.SnowflakeType) -> ari.RedisPlayer:
        guild_id = str(guild_id)

        try:
            return self._players[guild_id]
        except KeyError:
            player = self._players[guild_id] = self.__create_player(guild_id)
            weakref.finalize(player, log.debug, "player of guild %s got garbage collected", guild_id)
            return player

    def __get_player_state(self, guild_id: int) -> andesite.AbstractPlayerState:
        return self.get_player(guild_id).andesite_state

    def __get_voice_update(self, guild_id: str) -> VoiceUpdate:
        try:
            value = self._voice_updates[guild_id]
        except KeyError:
            value = self._voice_updates[guild_id] = VoiceUpdate(None, None)

        return value

    async def on_player_event(self, event: Any) -> None:
        if isinstance(event, events.AriEvent):
            kwargs = event.get_kwargs()
            kwargs["options"] = wamp.PublishOptions(acknowledge=True)

            log.debug("publishing event: %s", event)
            await self._session.publish(event.uri, *event.get_args(), **kwargs)

    async def on_andesite_track_end(self, event: andesite.TrackEndEvent) -> None:
        player = self.get_player(event.guild_id)
        await player.on_track_end(event)

    async def get_track_info(self, eid: str) -> ari.ElakshiTrack:
        await self._session.call("io.giesela.elakshi.get", eid)
        raise NotImplementedError

    @wamp.subscribe("com.discord.on_voice_state_update")
    async def on_voice_state_update(self, update: Any) -> None:
        if int(update["user_id"]) != self.config.andesite.user_id:
            return

        log.debug("received voice state update: %s", update)

        try:
            guild_id = update["guild_id"]
        except KeyError:
            log.debug("voice state update has no guild id, ignoring")
            return

        voice_update = self.__get_voice_update(guild_id)
        voice_update.state_update = update
        await self.__on_voice_update(voice_update)

    @wamp.subscribe("com.discord.on_voice_server_update")
    async def on_voice_server_update(self, update: Any) -> None:
        log.debug("received voice server update: %s", update)
        voice_update = self.__get_voice_update(update["guild_id"])
        voice_update.server_update = update
        await self.__on_voice_update(voice_update)

    async def __on_voice_update(self, update: VoiceUpdate) -> None:
        if not update.done:
            log.debug("not ready to send voice update yet: %s", update)
            return

        guild_id = int(update.guild_id)
        log.debug("sending voice server update for %s", guild_id)
        await self._andesite_ws.voice_server_update(guild_id, update.session_id, update.server_update)

        player = self.get_player(guild_id)

        channel_id = update.channel_id
        if channel_id:
            await player.on_connect(channel_id)
        else:
            await player.on_disconnect()

    @wamp.register("connect")
    async def connect(self, guild_id: ari.SnowflakeType, channel_id: ari.SnowflakeType) -> None:
        log.debug("connecting player in guild %s to %s", guild_id, channel_id)
        await self._session.call("com.discord.update_voice_state", guild_id, channel_id)

    @wamp.register("disconnect")
    async def disconnect(self, guild_id: ari.SnowflakeType) -> None:
        log.debug("disconnecting player in guild %s", guild_id)
        await self._session.call("com.discord.update_voice_state", guild_id)

    @wamp.register("queue")
    async def queue(self, guild_id: ari.SnowflakeType, page: int, entries_per_page: int = 50) -> List[Dict[str, str]]:
        player = self.get_player(guild_id)
        entries = await ari.get_entry_list_page(player.queue, page, entries_per_page)
        ser_entries = [entry.as_dict() for entry in entries]
        return ser_entries

    @wamp.register("history")
    async def history(self, guild_id: ari.SnowflakeType, page: int, entries_per_page: int = 50):
        player = self.get_player(guild_id)
        entries = await ari.get_entry_list_page(player.history, page, entries_per_page)
        ser_entries = [entry.as_dict() for entry in entries]
        return ser_entries

    @wamp.register("enqueue")
    async def enqueue(self, guild_id: ari.SnowflakeType, eid: str) -> str:
        player = self.get_player(guild_id)

        entry = ari.Entry(ari.new_aid(), eid)
        await player.enqueue(entry)

        return entry.aid

    @wamp.register("dequeue")
    async def dequeue(self, guild_id: ari.SnowflakeType, aid: str) -> bool:
        return await self.get_player(guild_id).dequeue(aid)

    @wamp.register("move")
    async def move(self, guild_id: ari.SnowflakeType, aid: str, index: int, whence: str) -> bool:
        try:
            whence = ari.Whence(whence)
        except ValueError:
            raise wamp.ApplicationError(
                wamp.ApplicationError.INVALID_ARGUMENT,
                "invalid whence argument",
                possible_values=[val.name for val in ari.Whence],
            )

        return await self.get_player(guild_id).move(aid, index, whence)

    @wamp.register("pause")
    async def pause(self, guild_id: ari.SnowflakeType, pause: bool) -> None:
        await self.get_player(guild_id).pause(pause)

    @wamp.register("set_volume")
    async def set_volume(self, guild_id: ari.SnowflakeType, volume: float) -> None:
        await self.get_player(guild_id).set_volume(volume)

    @wamp.register("seek")
    async def seek(self, guild_id: ari.SnowflakeType, position: float) -> None:
        await self.get_player(guild_id).seek(position)

    @wamp.register("skip_next")
    async def skip_next(self, guild_id: ari.SnowflakeType) -> None:
        await self.get_player(guild_id).next()

    @wamp.register("skip_next_chapter")
    async def skip_next_chapter(self, guild_id: ari.SnowflakeType) -> None:
        await self.get_player(guild_id).next_chapter()

    @wamp.register("skip_previous")
    async def skip_previous(self, guild_id: ari.SnowflakeType) -> None:
        await self.get_player(guild_id).previous()

    @wamp.register("skip_previous_chapter")
    async def skip_previous_chapter(self, guild_id: ari.SnowflakeType) -> None:
        await self.get_player(guild_id).previous_chapter()


async def create_ari_server(config: ari.Config) -> AriServer:
    """Create the Ari server."""
    redis = await aioredis.create_redis_pool(config.redis.address)
    await redis.select(config.redis.database)
    andesite_ws = andesite.create_pool((), config.andesite.get_node_tuples(),
                                       user_id=config.andesite.user_id)
    server = AriServer(config, redis, config.redis.namespace, andesite_ws)

    return server


def create_component(server: AriServer, config: ari.Config) -> Component:
    """Create the WAMP component."""
    component = Component(
        realm=config.realm,
        transports=config.transports,
    )

    @component.on_join
    async def joined(session: wamp.ISession, details: wamp.SessionDetails) -> None:
        log.info("joined session (realm: %s)", details.realm)
        server._session = session

        await session.register(server, prefix=f"io.giesela.ari.")
        await session.subscribe(server)

    return component
