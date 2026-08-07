This page explains how to connect to a running BotWave instance remotely using the WebSocket remote shell.

> [!NOTE]
> This page assumes you're already familiar with the basics. If not, start with [Main/Basic Usage](https://github.com/dpipstudio/botwave/wiki/Basic-usage).

## How it works

BotWave includes a built-in **remote command handler**: a WebSocket server that gives you a live shell into a running BotWave instance from any machine on your network (or the internet, if the port is exposed). Once connected, you can run any BotWave command as if you were sitting at the prompt. Log output from BotWave is also mirrored to your session in real time.

> [!IMPORTANT]
> The remote shell is **not** the same as the main BotWave WebSocket server used by clients. It runs on a completely separate port and is purely for remote control.


## Enabling the Remote Shell

The remote shell is disabled by default. To enable it, pass `--rc <port>` when starting BotWave:

**Server:**
```bash
bw-server --rc 9939
```

**Local client:**
```bash
sudo bw-local --rc 9939
```

You can also set it via environment variable (or `.env` file):
```
REMOTE_CMD_PORT=9939
```

Once started, you'll see:
```
[SERVER] Remote CLI server started on ws://0.0.0.0:9939
```

> [!TIP]
> Pick any port that isn't already in use. `9939` is the standard choice since it's right next to BotWave's defaults (`9938` and `9921`).


## Securing it with a Passkey

By default, anyone who can reach the port can connect. To require a password, pass `--pk` alongside `--rc`:

```bash
bw-server --rc 9939 --pk MyRemotePass
```

When a client connects, they'll be prompted for the password. If they don't respond within 60 seconds, the connection is dropped automatically.

> [!WARNING]
> If you're exposing the remote shell port to the internet, **always** use a passkey. Without one, anyone who reaches the port has full control of your BotWave instance.

The timeout duration can be adjusted with the `REMOTE_CMD_PWD_TIMEOUT` environment variable (in seconds, default: `60`).


## Connecting to the Remote Shell

The best tool for connecting remotely to botwave is [BWSC](https://github.com/douxxtech/bwsc). It supports color-coded output, command history, and works out of the box with both authenticated and unauthenticated servers.

### Using BWSC (recommended)

```bash
# Install (requires Node.js and npm)
npm i -g bwsc

# Connect
bwsc 192.168.1.10:9939

# Connect with a passkey
bwsc 192.168.1.10:9939 MyRemotePass
```

The host argument is flexible: `bwsc 192.168.1.10:9939`, `bwsc ws://192.168.1.10:9939`, and `bwsc wss://example.com:443` all work. If you just pass `localhost`, it defaults to `ws://localhost:9939`.

BWSC also supports a fire-and-forget mode, useful for scripting:

```bash
bwsc 192.168.1.10:9939 MyRemotePass --fire "start all mysong.wav 88.5"
```


### Using any WebSocket client

Any generic WebSocket client works too. For example, with `websocat`:

```bash
# Install
npm i -g wscat

# Connect
wscat -c ws://192.168.1.10:9939
```

If a passkey is set, you'll see `Password: `. Type it and press Enter. On success, you'll get `OK.` and then the welcome message (if one is configured).

From there, type commands just like you would at the local BotWave prompt:
```
botwave> list
botwave> start all mysong.wav 88.5 true
botwave> stop all
```

To close the session cleanly, type `exit`. This disconnects you without affecting the running BotWave instance.

For security reasons, a few commands are blocked over the remote shell by default:

| Command | Why it's blocked |
|--|--|
| `get` | Exposes environment variables (may contain passkeys) |
| `set` | Can modify the runtime environment |
| `<` | Runs arbitrary shell commands on the host system |
| `\|` | Same as above, via pipe |

If you try to run one of these, you'll get:
```
[WARN] Hmmm, you can't do that. ;)
```

You can customize the blocked list via the `REMOTE_BLOCKED_CMD` environment variable (comma-separated):
```
REMOTE_BLOCKED_CMD=get,set,<,|,kick
```

### Unblocking everything

If you're running in a fully trusted, isolated environment and need unrestricted access, you can bypass the block list entirely:

```
ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING=true
```

> [!CAUTION]
> This gives remote clients full root shell access to the host system via `<` and `|`. Only use this if you fully trust everyone who can reach the port, and ideally with a passkey and a firewall.


## Welcome Message

You can configure a message that's sent to every client upon connecting:

```
REMOTE_CMD_WELCOME="Welcome to the BotWave remote shell. Be nice."
```


## Notes

- **Log mirroring**: All BotWave log output is forwarded to every connected remote client in real time. You'll see broadcasts starting, clients connecting, errors, etc., just like at the local prompt.
- **No variable interpolation**: `{VAR}` syntax is **not** expanded for commands sent via the remote shell. This is intentional, for security.
- **Multiple clients**: Multiple remote clients can be connected simultaneously. Commands from any of them are executed in order.


## Quick Reference

| Flag | Description |
|--|--|
| `--rc <port>` | Enable the remote shell on the given port |
| `--pk <passkey>` | Require a password to connect |

| Variable | Default | Description |
|--|--|--|
| `REMOTE_CMD_PORT` | *(none)* | Port for the remote shell. Disabled if not set. |
| `PASSKEY` | *(none)* | Password required to connect. |
| `REMOTE_BLOCKED_CMD` | `get,set,<,\|` | Comma-separated list of blocked commands. |
| `ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING` | `false` | Bypass the blocked command list entirely. |
| `REMOTE_CMD_WELCOME` | *(none)* | Message sent to clients on connect. |
| `REMOTE_CMD_PWD_TIMEOUT` | `60` | Seconds before an unauthenticated connection is dropped. |