import asyncio
import logging

import click

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


def _setup_logging() -> None:
    root = logging.getLogger()

    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter("{levelname} {name}: {message}", style="{")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)


async def run(config: ari.Config, *, loop: asyncio.AbstractEventLoop) -> None:
    server = await ari.create_ari_server(config, loop=loop)
    component = ari.create_component(server)

    log.info("starting component")
    await component.start(loop=loop)


@click.command()
@click.option("--config", "-c", type=click.Path(), default="config.toml")
def main(config: str) -> None:
    """Run the Ari Component."""
    _setup_logging()
    _install_uvloop()

    c = ari.load_config(config)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(c, loop=loop))


if __name__ == "__main__":
    main()
