# BotWave - Local Client | Documentation

> This tool is included in the **CLIENT** install.

BotWave Local Client is a standalone application designed to broadcast audio files over FM radio using a Raspberry Pi. It utilizes the PiWave module to handle the broadcasting functionality.

## Requirements

- Raspberry Pi (Officially working: RPI 0, 1, 2, 3, and 4)
- Root Access
- Python >= 3.9
- [bw_custom](https://github.com/dpipstudio/bw_custom) installed
- [PiWave](https://github.com/douxxtech/piwave) Python module

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Safety Note**: To minimize interference and stay within your intended frequency range, it is strongly recommended to use a band-pass filter when operating BotWave.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions, equipment, and knowledge of regulations before using BotWave for broadcasting purposes.

We highly recommend using the official installer (Check the [main README](/README.md)). Note that if you aren't on a Raspberry Pi, the client is very unlikely to work.

## Usage

To start the BotWave Local Client, use the following command:
```bash
sudo bw-local [-h] [--upload-dir UPLOAD_DIR] [--handlers-dir HANDLERS_DIR] [--skip-checks | --no-skip-checks] [--daemon | --no-daemon] [--rc RC] [--pk PK] [--talk | --no-talk] [--config CONFIG]
```

### Arguments

- `--upload-dir`: The directory to store uploaded files (default: `/opt/BotWave/uploads/`).
- `--handlers-dir`: The directory to retrieve `l_` handlers from (default: `/opt/BotWave/handlers/`).
- `--skip-checks`: Skip system requirements checks.
- `--daemon`: Run in daemon mode (non-interactive).
- `--rc`: Port for the remote CLI. You can connect remotely to your websocket server via [botwave.dpip.lol](https://botwave.dpip.lol/websocket/). For an API documentation, check [misc_doc/websocket.md](/misc_doc/websocket.md).
- `--pk`: Optional passkey for websocket authentication.
- `--talk`: Show the debug logs.
- `--config`: Path to a config file to load into environment.

### Example

```bash
sudo bw-local --upload-dir /tmp/my_uploads --skip-checks --rc 9939
```

### Available Commands

Once the client is running, you can use the following commands:

| Command | Usage | Description |
| :--- | :--- | :--- |
| `start` | `botwave> start <file> [frequency] [loop] [ps] [rt] [pi]` | Start broadcasting a WAV file. |
| `stop` | `botwave> stop` | Stop the current broadcast. |
| `live` | `botwave> live [frequency] [ps] [rt] [pi]` | Start a live broadcast. |
| `queue` | `botwave> queue ?` | Manages the queue. |
| `sstv` | `botwave> sstv <image path> [mode] [output wav name] [freq] [loop] [ps] [rt] [pi]` | Start broadcasting an image converted to SSTV (requires `pysstv`, `numpy`, `pillow`). |
| `morse` | `botwave> morse <text\|file path> [wpm] [freq] [loop] [ps] [rt] [pi]` | Start broadcasting text converted to Morse code. |
| `lf` | `botwave> lf` | List files in the upload directory. |
| `rm` | `botwave> rm <filename\|all>` | Remove a file from the upload directory. |
| `upload` | `botwave> upload <file\|folder>` | Upload a file to the upload directory. |
| `dl` | `botwave> dl <url> [destination]` | Download a file from an external URL. |
| `handlers` | `botwave> handlers [filename]` | List all handlers or commands in a specific handler file. |
| `<` | `botwave> < <command>` | Run a shell command on the main OS. |
| `\|` | `botwave> \| <command>` | Run a shell command and pipe each output line as a BotWave command. |
| `get` | `botwave> get <keys\|*>` | Get one or more environment variable(s). |
| `set` | `botwave> set <key> <value> [immutable]` | Set an environment variable. |
| `status` | `botwave> status` | Show current broadcast and remote status. |
| `help` | `botwave> help` | Display the help message. |
| `exit` | `botwave> exit` | Exit the application. |

> [!WARNING]
> `sstv` and `morse` command modules are not installed by default. Install them with `[sudo /opt/BotWave/venv/bin/]pip install pysstv numpy pillow`

### Supported handlers
- `l_onready`: When the client is ready (on startup).
- `l_onstart`: When a broadcast has been started.
- `l_onstop`: When a broadcast has been stopped (manually).
- `l_onwsjoin`: When a remote CLI client connects.
- `l_onwsleave`: When a remote CLI client disconnects.
- `l_onexit`: When the client exits.

Check [misc_doc/handlers.md](/misc_doc/handlers.md) for a better documentation.