from __future__ import annotations

import logging
import weakref
from typing import Any, Dict, List, Optional

import aioredis
import andesite
from autobahn.asyncio.component import Component
from autobahn.wamp import ISession, PublishOptions, SessionDetails, register, subscribe

import ari
from ari import events

__all__ = ["AriServer", "create_ari_server", "create_component"]

log = logging.getLogger(__name__)


class AriServer(ari.PlayerManagerABC):
    __slots__ = ("config",
                 "_redis", "_manager_key", "_andesite_ws",
                 "_players",
                 "_session",
                 "_voice_session_id")

    config: ari.Config

    _redis: aioredis.Redis
    _manager_key: str
    _andesite_ws: andesite.WebSocketInterface

    _players: weakref.WeakValueDictionary

    _session: Optional[ISession]

    _voice_session_id: Optional[str]

    def __init__(self, config: ari.Config, redis: aioredis.Redis, manager_key: str,
                 andesite_ws: andesite.WebSocketInterface) -> None:
        super().__init__()
        self.config = config

        self._redis = redis
        self._manager_key = manager_key
        self._andesite_ws = andesite_ws
        andesite_ws.event_target.on(andesite.TrackEndEvent, self.on_andesite_track_end)

        self._players = weakref.WeakValueDictionary()

        self._session = None

        self._voice_session_id = None

    def _create_player(self, guild_id: int) -> ari.RedisPlayer:
        player = ari.RedisPlayer(self, self._redis, f"{self._manager_key}:{guild_id}", self._andesite_ws, guild_id)
        player.observable.on(callback=self.on_player_event)
        return player

    def get_player(self, guild_id: int) -> ari.RedisPlayer:
        try:
            return self._players[guild_id]
        except KeyError:
            player = self._players[guild_id] = self._create_player(guild_id)
            weakref.finalize(player, log.debug, "player of guild %s got garbage collected", guild_id)
            return player

    async def on_player_event(self, event: Any) -> None:
        if isinstance(event, events.AriEvent):
            kwargs = event.get_kwargs()
            kwargs["options"] = PublishOptions(acknowledge=True)

            log.debug("publishing event: %s", event)
            await self._session.publish(event.uri, *event.get_args(), **kwargs)

    async def on_andesite_track_end(self, event: andesite.TrackEndEvent) -> None:
        player = self.get_player(event.guild_id)
        await player.on_track_end(event)

    async def get_track_info(self, eid: str) -> ari.ElakshiTrack:
        await self._session.call("io.giesela.elakshi.get", eid)
        raise NotImplementedError

    @subscribe("com.discord.on_voice_state_update")
    async def on_voice_state_update(self, update: Any) -> None:
        if int(update["user_id"]) != self.config.andesite.user_id:
            return

        log.debug("received voice state update: %s", update)

        self._voice_session_id = update["session_id"]

        try:
            guild_id = int(update["guild_id"])
        except KeyError:
            return

        player = self.get_player(guild_id)

        channel_id = update["channel_id"]

        if not channel_id:
            await player.on_disconnect()
        else:
            await player.on_connect(int(channel_id))

    @subscribe("com.discord.on_voice_server_update")
    async def on_voice_server_update(self, update: Any) -> None:
        log.debug("received voice server update: %s", update)
        if self._voice_session_id is None:
            return

        await self._andesite_ws.voice_server_update(int(update["guild_id"]), self._voice_session_id, update)

    @register("connect")
    async def connect(self, guild_id: int, channel_id: int) -> None:
        log.debug("connecting player in guild %s to %s", guild_id, channel_id)
        await self._session.call("com.discord.update_voice_state", guild_id, channel_id)

    @register("disconnect")
    async def disconnect(self, guild_id: int) -> None:
        log.debug("disconnecting player in guild %s", guild_id)
        await self._session.call("com.discord.update_voice_state", guild_id)

    @register("queue")
    async def queue(self, guild_id: int, page: int, entries_per_page: int = 50) -> List[Dict[str, str]]:
        player = self.get_player(guild_id)
        entries = await ari.get_entry_list_page(player.queue, page, entries_per_page)
        ser_entries = [entry.as_dict() for entry in entries]
        return ser_entries

    @register("history")
    async def history(self, guild_id: int, page: int, entries_per_page: int = 50):
        player = self.get_player(guild_id)
        entries = await ari.get_entry_list_page(player.history, page, entries_per_page)
        ser_entries = [entry.as_dict() for entry in entries]
        return ser_entries

    @register("enqueue")
    async def enqueue(self, guild_id: int, eid: str) -> str:
        player = self.get_player(guild_id)

        entry = ari.Entry(ari.new_aid(), eid)
        await player.enqueue(entry)

        return entry.aid

    @register("move")
    async def move(self, guild_id: int, aid: str, index: int) -> bool:
        player = self.get_player(guild_id)
        return await player.queue.move(aid, index)

    @register("remove")
    async def remove(self, guild_id: int, aid: str) -> bool:
        player = self.get_player(guild_id)
        return await player.queue.remove(aid)

    @register("pause")
    async def pause(self, guild_id: int, pause: bool) -> None:
        player = self.get_player(guild_id)
        await player.pause(pause)

    @register("get_volume")
    async def get_volume(self, guild_id: int) -> float:
        player = self.get_player(guild_id)
        return await player.get_volume()

    @register("set_volume")
    async def set_volume(self, guild_id: int, volume: float) -> None:
        player = self.get_player(guild_id)
        await player.set_volume(volume)

    @register("seek")
    async def seek(self, guild_id: int, position: float) -> None:
        player = self.get_player(guild_id)
        await player.seek(position)


async def create_ari_server(config: ari.Config) -> AriServer:
    """Create the Ari server."""
    redis = await aioredis.create_redis_pool(config.redis.address)
    await redis.select(config.redis.database)
    andesite_ws = andesite.create_pool((), config.andesite.get_node_tuples(),
                                       user_id=config.andesite.user_id)
    server = AriServer(config, redis, config.redis.namespace, andesite_ws)
    andesite_ws.state = andesite.State(state_factory=server.get_player)

    return server


def create_component(server: AriServer, config: ari.Config) -> Component:
    """Create the WAMP component."""
    component = Component(
        realm=config.realm,
        transports=config.transports,
    )

    @component.on_join
    async def joined(session: ISession, details: SessionDetails) -> None:
        log.info("joined session (realm: %s)", details.realm)
        server._session = session

        await session.register(server, prefix=f"io.giesela.ari.")
        await session.subscribe(server)

    return component
