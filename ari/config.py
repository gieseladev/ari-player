from typing import Dict, Iterable, List, Optional, Tuple, Union

import konfi

__all__ = ["Redis",
           "AndesiteNode", "Andesite",
           "Config", "load_config"]


@konfi.template()
class Redis:
    """Config for redis"""
    address: str
    namespace: str = "ari"
    database: int = 0


@konfi.template()
class AndesiteNode:
    """Config for an Andesite node"""
    url: str
    password: Optional[str]

    def as_tuple(self) -> Tuple[str, str]:
        return self.url, self.password


@konfi.template()
class Andesite:
    """Config for the Andesite nodes"""
    user_id: int
    nodes: List[AndesiteNode]

    def get_node_tuples(self) -> Iterable[Tuple[str, str]]:
        return (node.as_tuple() for node in self.nodes)


@konfi.template()
class Transport:
    """Transport configuration."""
    type: str = "websocket"
    url: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "type": self.type,
            "url": self.url,
        }


@konfi.template()
class Config:
    """Ari configuration"""
    redis: Redis
    andesite: Andesite

    realm: str
    transports: Union[List[Transport], str]

    def get_transports(self) -> Union[List[Dict[str, str]], str]:
        """Get the transports configuration in the format required by
        the component constructor."""
        if isinstance(self.transports, str):
            return self.transports
        else:
            return [transport.as_dict() for transport in self.transports]


def load_config(config_file: str) -> Config:
    """Load the ari config."""
    konfi.set_sources(
        konfi.FileLoader(config_file, ignore_not_found=True),
        konfi.Env("ARI_"),
    )

    return konfi.load(Config)
