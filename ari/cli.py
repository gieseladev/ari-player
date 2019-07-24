import argparse
import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ari import Config as AriConfig

log = logging.getLogger(__name__)


def _install_uvloop() -> None:
    try:
        import uvloop
    except ImportError:
        log.info("Not using uvloop")
    else:
        log.info("Using uvloop")
        uvloop.install()

        # gotta update txaio too!
        import txaio
        txaio.config.loop = asyncio.get_event_loop()


def _setup_logging() -> None:
    root = logging.getLogger()

    root.setLevel(logging.DEBUG)
    fmt = logging.Formatter("{levelname} {name}: {message}", style="{")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)


async def run(config: "AriConfig", *, loop: asyncio.AbstractEventLoop) -> None:
    import ari

    server = await ari.create_ari_server(config, loop=loop)
    component = ari.create_component(server, config)

    log.info("starting component")
    await component.start(loop=loop)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config", default="config.toml", help="specify the location of the config file.")
    parser.add_argument("--no-uvloop", action="store_true", default=False,
                        help="disable the use of uvloop. On Windows this is true regardless")

    return parser


def main() -> None:
    """Run the Ari Component."""
    args = get_parser().parse_args()

    _setup_logging()

    if not args.no_uvloop:
        _install_uvloop()

    import ari

    c = ari.load_config(args.config)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(c, loop=loop))


if __name__ == "__main__":
    main()
