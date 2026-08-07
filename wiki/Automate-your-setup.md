This page will guide you through automating your BotWave setup using handlers and systemd services.

> [!NOTE]
> Before following this guide, make sure you've completed [Base/Setup](https://github.com/dpipstudio/botwave/wiki/Setup) and are familiar with [Main/Basic Usage](https://github.com/dpipstudio/botwave/wiki/Basic-usage).

BotWave supports two main types of automation:

- **Handlers**: run commands automatically when specific events occur (a client connects, a broadcast starts, etc.)
- **Autorun**: start BotWave automatically when your system boots


## Handlers

Handlers are simple text files containing BotWave commands that run automatically when certain events trigger them. They live in the handlers directory (default: `/opt/BotWave/handlers`) and follow a specific naming convention.

### Naming conventions

The filename determines **when** the handler runs, and the extension determines **how** it logs:

**Server handlers** (for `bw-server`):

| Prefix | Triggers when... |
|--|--|
| `s_onready` | The server has fully started |
| `s_onexit` | The server will exit |
| `s_onstart` | A broadcast starts on any client |
| `s_onstop` | A broadcast stops on any client |
| `s_onconnect` | A client connects to the server |
| `s_ondisconnect` | A client disconnects from the server |
| `s_onwsjoin` | Someone connects via WebSocket remote shell |
| `s_onwsleave` | Someone disconnects from WebSocket remote shell |

**Local client handlers** (for `bw-local`):

| Prefix | Triggers when... |
|--|--|
| `l_onready` | The local client has fully started |
| `l_onexit` | The local client will exit |
| `l_onstart` | A broadcast starts |
| `l_onstop` | A broadcast stops |
| `l_onwsjoin` | Someone connects via WebSocket remote shell |
| `l_onwsleave` | Someone disconnects from WebSocket remote shell |

**Extensions:**
- `.hdl`: standard handler, logs each command as it runs
- `.shdl`: silent handler, no log output (useful for keeping things clean)

### File format

Each line is a command, exactly as you'd type it in the BotWave prompt. Empty lines and lines starting with `#` are ignored.

```plaintext
# This runs when the server starts
list
< echo "BotWave Server is ready!"
```

### Variable interpolation

Handlers support `{VAR}` syntax to inject environment variables directly into BotWave commands:

```plaintext
# Kick a client using its injected hostname
kick {BW_CLIENT_HOSTNAME} "Kicked by handler"
```

### Environment variables

BotWave injects context as environment variables when a handler runs. These are available to any shell command called from within the handler.

**Always available:**

| Variable | Description |
|--|--|
| `BW_SYSTEM_HOSTNAME` | Hostname of the machine running BotWave |
| `BW_SYSTEM_MACHINE` | Machine architecture |
| `BW_SYSTEM_SYSTEM` | OS name |
| `BW_SYSTEM_PROTO` | Protocol version |
| `BW_UPLOAD_DIR` | Upload directory path |
| `BW_HANDLERS_DIR` | Handlers directory path |
| `BW_WS_PORT` | WebSocket port (`0` if unset) |
| `BW_PASSKEY_SET` | `true` or `false` |
| `BW_TRANSACTION_ID` | User-provided transaction ID or empty |
| `BW_ARGV0`, `BW_ARGV1`, ... | Arguments from the last executed BotWave command (0-indexed) |

**Always available (Server Only)**

| Variable | Description |
|---|---|
| `BW_SERVER_CONNECTED_CLIENTS` | Comma-separated list of hostnames of all connected clients |


**Event-specific:**

| Event | Extra variables |
|--|--|
| `l_onstart` / `s_onstart` | `BW_BROADCAST_FILE`, `BW_BROADCAST_FREQ` |
| `l_onstop` / `s_onstop` | `BW_BROADCAST_FILE` |
| `s_onconnect` / `s_ondisconnect` | `BW_CLIENT_ID`, `BW_CLIENT_HOSTNAME`, `BW_CLIENT_MACHINE`, `BW_CLIENT_SYSTEM`, `BW_CLIENT_PROTO`, `BW_CLIENT_CONNECTED_AT` |

> [!NOTE]
> For `s_onconnect` and `s_ondisconnect`, `BW_CLIENT_*` variables refer to the remote client that connected, while `BW_SYSTEM_*` always refers to the server itself.

> [!NOTE]
> `{VAR}` interpolation only applies to commands run from handlers. Commands sent via the WebSocket remote shell are **not** interpolated for security reasons.


### Creating and managing handlers

BotWave includes `bw-nandl`, a built-in handler editor and validator. It's the recommended way to create and manage handlers.

```bash
# Create a new handler
sudo bw-nandl s_onready.hdl

# List all handlers
sudo bw-nandl list

# View a handler's contents
sudo bw-nandl show s_onready.hdl

# Edit an existing handler
sudo bw-nandl open s_onready.hdl
```

> [!TIP]
> `bw-nandl` defaults to `/opt/BotWave/handlers/` if you don't provide a full path. You can also specify a full path: `sudo bw-nandl /path/to/myhandler.hdl`

You can also list and inspect handlers from within BotWave:

```bash
botwave> handlers              # list all handlers
botwave> handlers s_onready.hdl   # show commands in a specific handler
```


### Handler examples

#### List clients when a new one connects

**`s_onconnect.shdl`**
```plaintext
> echo "New client connected, listing all clients..."
list
```

#### Log every broadcast silently

**`s_onstart.shdl`**
```plaintext
< echo "[$(date)] Broadcast started: $BW_BROADCAST_FILE on $BW_BROADCAST_FREQ MHz" >> /opt/BotWave/broadcast.log
```

#### Auto-start a playlist when the local client is ready

**`l_onready.hdl`**
```plaintext
queue +*
queue !
```

#### Client whitelist on connect

This example uses a shell script to kick any client not on an allowed list.

**`/opt/BotWave/scripts/whitelist.sh`**
```sh
#!/bin/sh
WHITELIST="pi pi1 radpi"
HOSTNAME="$BW_CLIENT_HOSTNAME"
FOUND=0

for h in $WHITELIST; do
    if [ "$h" = "$HOSTNAME" ]; then
        FOUND=1
        break
    fi
done

if [ "$FOUND" -ne 1 ]; then
    echo "< echo \"${HOSTNAME} is not on the whitelist. Kicking...\""
    echo "kick ${HOSTNAME} \"Not on whitelist\""
fi
```

**`s_onconnect.hdl`**
```plaintext
| sh /opt/BotWave/scripts/whitelist.sh
```

> [!NOTE]
> The pipe (`|`) command takes every line of the given shell command out and executes it as a BotWave command.  
> In this example, the script will return `< echo [...]` and `kick [...]`. Both commands will then be executed as BotWave commands. 

### Multiple handlers and execution order

You can create multiple handler files with the same prefix. They'll all execute. Handlers run in **alphabetical order**, so use numbered names to control the sequence:

```
s_onready_01_sync.hdl
s_onready_02_start.hdl
s_onready_03_notify.hdl
```


## Autorun

BotWave can automatically start when your system boots using systemd services. This is perfect for dedicated broadcasting setups that should always be running.

### Installing autorun

```bash
sudo bw-autorun <mode> [arguments]
```

Where `<mode>` is one of `client`, `server`, `local`, or `all`. Any arguments after the mode are passed directly to BotWave on startup.

The service starts immediately after installation. No reboot needed.

### Examples

#### Server with authentication
```bash
sudo bw-autorun server --pk MySecurePass --start-asap
```

#### Client connecting to a remote server
```bash
sudo bw-autorun client 192.168.1.10 --pk MySecurePass
```

#### Local client with remote shell
```bash
sudo bw-autorun local --rc 8080 --pk LocalPass
```

### Managing autorun services

```bash
# Using bw-autorun
sudo bw-autorun --start client
sudo bw-autorun --stop server
sudo bw-autorun --restart local
sudo bw-autorun --status client       # shows status + recent logs
sudo bw-autorun --uninstall client

# Using systemctl directly
sudo systemctl status bw-client
sudo systemctl start bw-server
sudo systemctl stop bw-local
sudo journalctl -u bw-client -f       # follow logs in real time
```

> [!TIP]
> `bw-autorun --status` is especially handy as it shows both the service status and recent log entries in one command.


## Complete Example: Automated Music Station

Here's a full example combining handlers and autorun to run a 24/7 music station that starts on boot, syncs music to clients, and loops through a playlist automatically.

### Server setup

```bash
sudo bw-autorun server --pk TheBestStation
```

Create `s_onready_1_sync.shdl`:
```bash
sudo bw-nandl s_onready_1_sync.shdl
```
```plaintext
# Show server IP
< echo "My IP is: $(hostname -I)"

# Wait for clients to connect
< sleep 20

# Sync music library to all clients
sync all /home/radio/music/
```

Create `s_onready_2_start.shdl`:
```bash
sudo bw-nandl s_onready_2_start.shdl
```
```plaintext
< echo "Starting broadcast at $(date)"

# Queue all files and start looping at 90 MHz
queue +*
queue !all,90,true
```

### Client setup

```bash
sudo bw-autorun client 192.168.1.10 --pk TheBestStation
```

### Verify everything is running

```bash
sudo bw-autorun --status server
sudo bw-autorun --status client
sudo journalctl -u bw-server -f
```

Your station will now start automatically on boot, sync music, and broadcast continuously, restarting itself if anything crashes.


> [!TIP]
> Start small: get a simple handler working first, then add autorun, then combine them. Building up gradually is much easier than trying to configure everything at once.

> [!NOTE]
> Want to see a real-world automation example? Check out the [WebSocket To TCP](https://github.com/douxxtech/bw_wtt) project and its BotWave implementation.