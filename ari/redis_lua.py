import hashlib
import itertools
import logging
import textwrap
from typing import AnyStr, Collection, Generic, Iterable, Optional, TypeVar, Union

import aioredis.abc

__all__ = ["NoScriptError", "RedisLua"]

log = logging.getLogger(__name__)

DEFAULT = object()


def get_sha1_digest(data: bytes) -> bytes:
    m = hashlib.sha1()
    m.update(data)
    return m.digest()


class NoScriptError(aioredis.ReplyError):
    MATCH_REPLY = "NOSCRIPT No matching script."


HasRedisExecute = Union[aioredis.Redis, aioredis.abc.AbcConnection]

T = TypeVar("T")


class RedisLua(Generic[T]):
    __slots__ = ("__code", "__sha_digest")

    __code: bytes
    __sha_digest: bytes

    def __init__(self, code: AnyStr) -> None:
        if isinstance(code, str):
            code = code.encode()

        self.__code = code.strip()
        self.__sha_digest = get_sha1_digest(self.__code)

    def __hash__(self) -> int:
        return hash(self.__sha_digest)

    def __repr__(self) -> str:
        indented_code = textwrap.indent(self.__code, "  ")
        return f"RedisLua(\"\"\"\n{indented_code}\n\"\"\")"

    def __str__(self) -> str:
        return f"RedisLua#{self.__sha_digest}"

    async def _evalsha(self, redis: HasRedisExecute, key_count: int, *args: Iterable, **kwargs) -> T:
        return await redis.execute(b"EVALSHA", self.__sha_digest, key_count, *args, **kwargs)

    async def _eval(self, redis: HasRedisExecute, key_count: int, *args: Iterable, **kwargs) -> T:
        return await redis.execute(b"EVAL", self.__code, key_count, *args, **kwargs)

    async def eval(self, redis: HasRedisExecute, keys: Collection[AnyStr], args: Iterable, *,
                   encoding: Optional[str] = DEFAULT) -> T:
        kwargs = {}
        if encoding is not DEFAULT:
            kwargs["encoding"] = encoding

        try:
            return await self._evalsha(redis, len(keys), *itertools.chain(keys, args), **kwargs)
        except NoScriptError:
            log.info("%s script not cached yet, using eval.")
            return await self._eval(redis, len(keys), *itertools.chain(keys, args), **kwargs)
