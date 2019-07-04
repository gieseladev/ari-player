from __future__ import annotations

import asyncio
import logging
from typing import Any

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

    @register("enqueue")
    async def enqueue(self, guild_id: int, eid: str) -> str:
        player = self._manager.get_player(guild_id)

        e = ari.Entry(ari.new_aid(), eid)
        await player.queue.add_end(e)

        return e.aid


async def create_ari_server(config: ari.Config, *, loop: asyncio.AbstractEventLoop = None) -> AriServer:
    redis = await aioredis.create_redis_pool(config.redis.address, loop=loop)
    andesite_ws = andesite.create_andesite_pool((), config.andesite.get_node_tuples(),
                                                user_id=config.andesite.user_id,
                                                loop=loop)
    manager = ari.PlayerManager(redis, config.redis.namespace, andesite_ws)
    andesite_ws.state = andesite.AndesiteState[Any](state_factory=manager.get_player)

    return AriServer(config, manager)


def create_component(server: AriServer) -> Component:
    component = Component(
        realm=server.config.realm,
    )

    @component.on_join
    async def joined(session: ISession, details: SessionDetails) -> None:
        log.info("joined session %s: %s", session, details)
        giesela_uri = server.config.giesela_uri
        await session.register(server, preifx=f"{giesela_uri}.ari.")

    return component
