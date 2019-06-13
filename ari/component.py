""""""

import logging

from autobahn.asyncio.component import Component
from autobahn.wamp import ISession, SessionDetails, register

__all__ = []

log = logging.getLogger(__name__)


class AriServer:
    @register("enqueue")
    async def enqueue(self) -> None:
        pass


def create_ari_component() -> Component:
    ari_server = AriServer()

    component = Component()

    @component.on_join
    async def joined(session: ISession, details: SessionDetails) -> None:
        await session.register(ari_server, preifx="io.giesela.ari.")

    return component
