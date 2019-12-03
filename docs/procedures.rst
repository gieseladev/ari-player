Procedures
==========

All procedures are prefixed with the *uri_prefix* config value which defaults to
``io.ari.``.
This prefix is configurable using the `uri_prefix` key, but this is mainly for
development purposes.

Player
------

connect     ``(guild id, channel id) -> void``
    Connect ari to the given voice channel.
disconnect  ``(guild id) -> void``
    Disconnect from the current voice channel.

queue   ``(guild id, page, *, entries_per_page = 50) -> Entry[]``
    Get a page from the queue.
history ``(guild id, page, *, entries_per_page = 50) -> Entry[]``
    Get a page from the play history.

enqueue ``(guild id, eid) -> aid``
    Add a track to the queue and get the entry's *aid*.
dequeue ``(guild id, aid) -> boolean``
    Remove an entry from the queue.
move    ``(guild id, aid, index, whence) -> boolean``
    Move an entry to a different position in the queue.

pause       ``(guild id, pause) -> void``
    Set the pause state of the player.
set_volume  ``(guild id, volume) -> void``
    Set the volume of the player.
seek        ``(guild id, position) -> void``
    Seek to a position in the current track.

skip_next       ``(guild id) -> void``
    Skip the current track.
skip_previous   ``(guild id) -> void``
    Replay the previous track.
    Adds the current track, if any, to the start of the queue.

Meta
----

These procedures are prefixed with "meta."

assert_ready    ``() -> void``
    Ensure that ari is ready to be used.
