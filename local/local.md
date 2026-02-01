# BotWave - Local Client | Documentation

> This tool is included in the **CLIENT** install.

BotWave Local Client is a standalone application designed to broadcast audio files over FM radio using a Raspberry Pi. It utilizes the PiWave module to handle the broadcasting functionality.

## Requirements

- Raspberry Pi (Officially working: RPI 0, 1, 2, 3, and 4)
- Root Access
- Python >= 3.6
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

### Installation


We highly recommand using the official installer (Check the [main README](/README.md)) -- Note that if you aren't on a raspberry pi, the client is very unlikely to work.

## Usage

To start the BotWave Local Client, use the following command:
```bash
sudo bw-local [--upload-dir UPLOAD_DIR] [--handlers-dir HANDLERS_DIR] [--skip-checks] [--daemon] [--ws PORT] [--pk PASSKEY] [--talk]
```

### Arguments

- `--upload-dir`: The directory to store uploaded files (default: `/opt/BotWave/uploads`).
- `--handlers-dir`: The directory to retrive l_ handlers from (default: `/opt/BotWave/handlers`)
- `--skip-checks`: Skip system requirements checks.
- `--daemon`: Run in daemon mode (non-interactive).
- `--ws`: Port for the WebSocket server. You can connect remotly to your websocket server via [botwave.dpip.lol](https://botwave.dpip.lol/websocket/). For an API documentation, check [misc_doc/websocket.md](/misc_doc/websocket.md).
- `--pk`: Optional passkey for websocket authentication.
- `--talk`: Makes PiWave (broadcast manager) output logs visible.



### Example

```bash
sudo bw-local --upload-dir /tmp/my_uploads --skip-checks --ws 9939
```

### Available Commands

Once the client is running, you can use the following commands:

- `start`: Start broadcasting a WAV file.  
    - Usage: `botwave> start <file> [frequency] [loop] [ps] [rt] [pi]`

- `stop`: Stop the current broadcast.  
    - Usage: `botwave> stop`
  
- `live`: Start a live broadcast.  
    - Usage: `botwave> live [frequency] [ps] [rt] [pi]`
  
- `queue`: Manages the queue. See the [`Main/Queue system`](https://github.com/dpipstudio/botwave/wiki/Queue-system) wiki page for more details.  
    - Usage: `botwave> queue ?`

- `sstv`: Start broadcasting an image converted to SSTV. For modes see [dnet/pySSTV](https://github.com/dnet/pySSTV/).  
    - Usage: `botwave> sstv <image path> [mode] [output wav name] [freq] [loop] [ps] [rt] [pi]`

- `sstv`: Start broadcasting text converted to morse.    
    - Usage: `botwave> sstv <image path> [mode] [output wav name] [freq] [loop] [ps] [rt] [pi]`

- `list`: List files in the specified directory (default: upload directory).  
    - Usage: `botwave> list [directory]`

- `upload`: Upload a file to the upload directory.  
    - Usage: `botwave> upload <file|folder>`

- `dl`: Downloads a file from an external URL.  
    - Usage: `botwave> dl <url> [destination]`

- `handlers`: List all handlers or commands in a specific handler file.  
    - Usage: `botwave> handlers [filename]`

- `<`: Run a shell command on the main OS.  
    - Usage: `botwave> < <command>`

- `help`: Display the help message.  
    - Usage: `botwave> help`

- `exit`: Exit the application.  
    - Usage: `botwave> exit`

> [!WARNING]
> `sstv` command modules are not installed by default. Install them with `[sudo /opt/BotWave/venv/bin/]pip install pysstv numpy pillow`

### Supported handlers
- `l_onready`: When the client is ready (on startup).
- `l_onstart`: When a broadcast has been start.
- `l_onstop`: When a broadcast has been stopped (manually).

Check [misc_doc/handlers.md](/misc_doc/handlers.md) for a better documentation.

---

![A DPIP Studio Project](https://madeby.dpip.lol)

![Made by Douxx](https://madeby.douxx.tech)