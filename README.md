# Ari Player

[![CircleCI](https://circleci.com/gh/gieseladev/ari-player.svg?style=svg)](https://circleci.com/gh/gieseladev/ari-player)

Giesela's player component.


## Prerequisites

Due to the nature of being a WAMP component, Ari needs a
[WAMP router](https://wamp-proto.org/implementations.html#routers).

Ari's current implementation uses
[Andesite](https://github.com/natanbc/andesite-node) as its audio
player, so at least one Andesite node is required.


### Required Components

Ari doesn't work all by itself, it assumes that the following components
are available in the same realm.

- [Wampus](https://github.com/gieseladev/wampus) `com.discord`
- [Elakshi](https://github.com/gieseladev/elakshi) `io.giesela.elakshi`


## Configuration

There are two different ways you can use to configure Ari. Using
Configuration file specified in the `--config` command-line option and
using environment variables (when both sources specify a key, the
environment variable takes precedence).

The following is a representation of the config:

```yaml
realm:  sample realm name
url:    "tcp://localhost:8000"

redis:
    address:    "redis://localhost:6379"  
    namespace:  ari  #------------------  optional
  
andesite:
  user_id:      123456789
  nodes:
    - url:      "ws://localhost:5000/websocket"
      password: very much secure  #------------ optional

sentry:  # optional
  dsn:  "https://very-long-and-optional-dsn@sentry.io"
```

To configure a value, say, redis.address, use the environment variable
name "ARI_REDIS_ADDRESS". I'm sure you can see the pattern, prepend
"ARI_" and use "_" as a delimiter. **If a key already contains an
underscore simply ignore it.** andesite.user_id becomes
"ARI_ANDESITE_USERID".
