# BotWave - Server | Documentation

> This tool is included in the **SERVER** install.

BotWave Server is a program designed to manage multiple BotWave clients, allowing for the upload and broadcast of audio files over FM radio using Raspberry Pi devices.

## Requirements

- Python >= 3.9

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Safety Note**: To minimize interference and stay within your intended frequency range, it is strongly recommended to use a band-pass filter when operating BotWave.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions, equipment, and knowledge of regulations before using BotWave for broadcasting purposes.

We highly recommend using the official installer (Check the [main README](/README.md)). If you don't want to or are not using a Linux distribution, find how to install it yourself. (Tip: on Windows, use WSL.)

## Usage

To start the BotWave Server, use the following command:

```bash
bw-server [-h] [--host HOST] [--port PORT] [--fport FPORT] [--pk PK] [--handlers-dir HANDLERS_DIR] [--start-asap | --no-start-asap] [--skip-checks | --no-skip-checks] [--rc RC] [--config CONFIG] [--daemon | --no-daemon]
```

### Arguments

- `--host`: The host address to bind the server to (default: `0.0.0.0`).
- `--port`: The port on which the server will listen (default: `9938`).
- `--fport`: The port on which the file transfer server will listen (default: `9921`).
- `--pk`: Optional passkey for client authentication.
- `--handlers-dir`: The directory to retrieve `s_` handlers from (default: `/opt/BotWave/handlers/`).
- `--start-asap`: Start broadcasting as soon as possible. Can cause desync between clients.
- `--skip-checks`: Skip checking for protocol updates.
- `--rc`: Port for the remote CLI. You can connect remotely to your websocket server via [botwave.dpip.lol](https://botwave.dpip.lol/websocket/). For an API documentation, check [misc_doc/websocket.md](/misc_doc/websocket.md).
- `--config`: Path to a config file to load into environment.
- `--daemon`: Run in daemon mode (non-interactive).

### Example

```bash
bw-server --host 0.0.0.0 --port 9938 --pk mypasskey
```

## Commands available

```
targets: Specifies the target clients. Can be 'all', a client ID, a hostname, or a comma-separated list of clients (client1,client2,etc).
```

| Command | Usage | Description |
| :--- | :--- | :--- |
| `start` | `botwave> start <targets> <file> [freq] [loop] [ps] [rt] [pi]` | Starts broadcasting on specified client(s). |
| `stop` | `botwave> stop <targets>` | Stops broadcasting on specified client(s). |
| `live` | `botwave> live <targets> [frequency] [ps] [rt] [pi]` | Start a live broadcast to client(s). |
| `queue` | `botwave> queue ?` | Manages the queue. |
| `sstv` | `botwave> sstv <targets> <image path> [mode] [output wav name] [freq] [loop] [ps] [rt] [pi]` | Start broadcasting an image converted to SSTV (requires `pysstv`, `numpy`, `pillow`). |
| `morse` | `botwave> morse <targets> <text\|file path> [wpm] [freq] [loop] [ps] [rt] [pi]` | Start broadcasting text converted to Morse code. |
| `list` | `botwave> list` | Lists all connected clients. |
| `upload` | `botwave> upload <targets> <path/of/file.wav\|path/of/folder/>` | Upload a file or a folder's files to specified client(s) (Experimental). |
| `sync` | `botwave> sync <targets\|path/of/folder/> <source_target\|path/of/folder/>` | Synchronize files across systems from a source (Experimental). |
| `dl` | `botwave> dl <targets> <url>` | Downloads a file from an external URL. |
| `lf` | `botwave> lf <targets>` | Lists broadcastable files on clients. |
| `rm` | `botwave> rm <targets> <filename\|all>` | Removes a file from client(s). |
| `kick` | `botwave> kick <targets> [reason]` | Kicks specified client(s) from the server. |
| `update` | `botwave> update <targets> [latest\|<version>]` | Request client(s) to update and restart. |
| `handlers` | `botwave> handlers [filename]` | List all handlers or commands in a specific handler file. |
| `<` | `botwave> < <command>` | Run a shell command on the main OS. |
| `\|` | `botwave> \| <command>` | Run a shell command and pipe each output line as a BotWave command. |
| `get` | `botwave> get <keys\|*>` | Get one or more environment variable(s). |
| `set` | `botwave> set <key> <value> [immutable]` | Set an environment variable. |
| `status` | `botwave> status [targets]` | Show server status, and optionally the broadcast status of client(s). |
| `exit` | `botwave> exit` | Stops and exits the BotWave server. |
| `help` | `botwave> help` | Shows the help. |

> [!WARNING]
> 1. `upload`/`sync` command support is experimental. Your client / server connection may crash or act strangely.
> 2. `sstv` and `morse` command modules are not installed by default. Install them with `[sudo /opt/BotWave/venv/bin/]pip install pysstv numpy pillow`

### Supported handlers
- `s_onready`: When the server is ready (on startup).
- `s_onstart`: When a broadcast has been started.
- `s_onstop`: When a broadcast has been stopped (manually).
- `s_onconnect`: When a client connects to the server.
- `s_ondisconnect`: When a client disconnects from the server.
- `s_onwsjoin`: When a remote CLI client connects.
- `s_onwsleave`: When a remote CLI client disconnects.
- `s_onexit`: When the server exits.

Check [misc_doc/handlers.md](/misc_doc/handlers.md) for a better documentation.