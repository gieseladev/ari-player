import argparse
import asyncio
import logging
import logging.config
from typing import TYPE_CHECKING

import txaio

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


def _setup_logging() -> None:
    logging.config.dictConfig({
        "version": 1,

        "formatters": {
            "stream": {
                "format": "{levelname} {name}: {message}",
                "style": "{",
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "stream",
            },
        },

        "loggers": {
            "ari": {
                "level": "DEBUG",
            },
            "andesite": {
                "level": "DEBUG",
            },
            "autobahn": {
                "level": "DEBUG",
            },
        },

        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    })


async def run(config: "AriConfig") -> None:
    """Run an Ari component with the given config."""
    txaio.config.loop = asyncio.get_event_loop()

    import ari

    server = await ari.create_ari_server(config)
    component = ari.create_component(server, config)

    log.info("starting component")
    await component.start()


def get_parser() -> argparse.ArgumentParser:
    """Get an argument parser for Ari's cli."""
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

    asyncio.run(run(c))


if __name__ == "__main__":
    main()
