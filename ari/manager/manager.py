from __future__ import annotations

import abc

import ari


class PlayerManagerABC(abc.ABC):
    """Manages multiple players."""
    __slots__ = ()

    @abc.abstractmethod
    def get_player(self, guild_id: ari.SnowflakeType) -> ari.PlayerABC:
        """Get the player for a guild.

        Args:
            guild_id: ID of the guild to get the player for.

        Returns:
            Player for the guild.
        """
        ...

    @abc.abstractmethod
    async def get_track_info(self, eid: str) -> ari.ElakshiTrack:
        """Get the Elakshi track from the eid.

        Args:
            eid: EID to get the track info for.

        Returns:
            Elakshi track.
        """
        ...

    @abc.abstractmethod
    async def get_audio_source(self, eid: str) -> ari.AudioSource:
        """Get an audio source for the eid.

        Args:
            eid: EID to get an audio source for.

        Returns:
            Audio source.
        """
        ...

    @abc.abstractmethod
    async def recover_state(self) -> None:
        """Load the previous state.

        Recovers all active players' state as well.

        This should be used to recover the state from a potential previous run.
        """
        ...
