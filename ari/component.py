from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List

import aioredis
import andesite
from autobahn.asyncio.component import Component
from autobahn.wamp import ISession, SessionDetails, register

import ari

__all__ = ["AriServer", "create_ari_server", "create_component"]

log = logging.getLogger(__name__)


class AriServer:
    config: ari.Config
    _manager: ari.PlayerManagerABC

    def __init__(self, config: ari.Config, manager: ari.PlayerManagerABC) -> None:
        self.config = config
        self._manager = manager

    @register("connect")
    async def connect(self, guild_id: int, channel_id: int) -> None:
        player = self._manager.get_player(guild_id)
        await player.connect(channel_id)

    @register("disconnect")
    async def disconnect(self, guild_id: int) -> None:
        player = self._manager.get_player(guild_id)
        await player.disconnect()

    @register("queue")
    async def queue(self, guild_id: int, page: int, entries_per_page: int = 50) -> List[Dict[str, str]]:
        player = self._manager.get_player(guild_id)
        entries = await ari.get_entry_list_page(player.queue, page, entries_per_page)
        ser_entries = [entry.as_dict() for entry in entries]
        return ser_entries

    @register("history")
    async def history(self, guild_id: int, page: int, entries_per_page: int = 50):
        player = self._manager.get_player(guild_id)
        entries = await ari.get_entry_list_page(player.history, page, entries_per_page)
        ser_entries = [entry.as_dict() for entry in entries]
        return ser_entries

    @register("enqueue")
    async def enqueue(self, guild_id: int, eid: str) -> str:
        player = self._manager.get_player(guild_id)

        entry = ari.Entry(ari.new_aid(), eid)
        player.enqueue(entry)

        return entry.aid

    @register("move")
    async def move(self, guild_id: int, aid: str, index: int) -> bool:
        player = self._manager.get_player(guild_id)
        return await player.queue.move(aid, index)

    @register("remove")
    async def remove(self, guild_id: int, aid: str) -> bool:
        player = self._manager.get_player(guild_id)
        return await player.queue.remove(aid)

    @register("pause")
    async def pause(self, guild_id: int, pause: bool) -> None:
        player = self._manager.get_player(guild_id)
        return await player.pause(pause)

    @register("get_volume")
    async def get_volume(self, guild_id: int) -> float:
        player = self._manager.get_player(guild_id)
        return await player.get_volume()

    @register("set_volume")
    async def set_volume(self, guild_id: int, volume: float) -> None:
        player = self._manager.get_player(guild_id)
        return await player.set_volume(volume)

    @register("seek")
    async def seek(self, guild_id: int, position: float) -> None:
        player = self._manager.get_player(guild_id)
        return await player.seek(position)


async def create_ari_server(config: ari.Config, *, loop: asyncio.AbstractEventLoop = None) -> AriServer:
    """Create the Ari server."""
    redis = await aioredis.create_redis_pool(config.redis.address, loop=loop)
    await redis.select(config.redis.database)
    andesite_ws = andesite.create_andesite_pool((), config.andesite.get_node_tuples(),
                                                user_id=config.andesite.user_id,
                                                loop=loop)
    manager = ari.PlayerManager(redis, config.redis.namespace, andesite_ws)
    andesite_ws.state = andesite.AndesiteState[Any](state_factory=manager.get_player)

    return AriServer(config, manager)


def create_component(server: AriServer) -> Component:
    """Create the WAMP component."""
    component = Component(
        realm=server.config.realm,
    )

    @component.on_join
    async def joined(session: ISession, details: SessionDetails) -> None:
        log.info("joined session %s: %s", session, details)
        giesela_uri = server.config.giesela_uri
        await session.register(server, preifx=f"{giesela_uri}.ari.")

    return component
