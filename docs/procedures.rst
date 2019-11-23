connect     (guild id, channel id) -> void
    Connect ari to the given voice channel.
disconnect  (guild id) -> void
    Disconnect from the current voice channel

queue   (guild id) -> void
history (guild id) -> void

enqueue (guild id, eid) -> aid
dequeue (guild id, aid) -> boolean
move    (guild id, aid, index, [whence]) -> boolean

pause       (guild id, pause) -> void
set_volume  (guild id, volume) -> void
seek        (guild id, position) -> void

skip_next       (guild id) -> void
skip_previous   (guild id) -> void


Meta
----

These procedures are prefixed with "meta."

assert_ready    () -> void

    Ensure that ari is ready to be used.
