import asyncio
import logging

import click
from autobahn.asyncio.component import run as run_component

import ari

log = logging.getLogger(__name__)


def _install_uvloop() -> None:
    try:
        import uvloop
    except ImportError:
        log.info("Not using uvloop")
    else:
        log.info("Using uvloop")
        uvloop.install()


async def run(config: ari.Config, *, loop: asyncio.AbstractEventLoop = None) -> None:
    server = await ari.create_ari_server(config, loop=loop)
    component = ari.create_component(server)

    log.info("starting %s", component)
    await run_component(component)


@click.command()
@click.option("--config", "-c", type=click.Path(), default="config.yml")
def main(config: str) -> None:
    """Run the Ari Component."""
    c = ari.load_config(config)
    asyncio.run(run(c))


if __name__ == "__main__":
    main()
