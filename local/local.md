# BotWave - Local Client | Documentation

> This tool is included in the **CLIENT** install.

BotWave Local Client is a standalone application designed to broadcast audio files over FM radio using a Raspberry Pi. It utilizes the PiWave module to handle the broadcasting functionality.

## Requirements

- Raspberry Pi (Officially working: RPI 0, 1, 2, 3, and 4)
- Root Access
- Python 3.x
- [PiFmRds](https://github.com/ChristopheJacquet/PiFmRds) installed
- [PiWave](https://github.com/dpipstudio/piwave) Python module

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions and knowledge of the regulations before using BotWave for broadcasting purposes.

### Installation


We highly recommand using the official installer (Check the [main README](/README.md)) -- If you don't want to or are not using a Linux distribution, find how to install it by yourself. (Tip: on windows, use wsl)

## Usage

To start the BotWave Local Client, use the following command:
```bash
sudo bw-local [--upload-dir UPLOAD_DIR] [--skip-checks]
```

### Arguments

- `--upload-dir`: The directory to store uploaded files (default: `/opt/BotWave/uploads`).
- `--handlers-dir`: The directory to retrive l_ handlers from (default: `/opt/BotWave/handlers`)
- `--skip-checks`: Skip system requirements checks.
* `--daemon`: Run in daemon mode (non-interactive).


### Example

```bash
sudo bw-local --upload-dir /tmp/my_uploads --skip-checks
```

### Available Commands

Once the client is running, you can use the following commands:

- `start`: Start broadcasting a WAV file.  
    - Usage: `botwave> start <file> [frequency] [ps] [rt] [pi] [loop]`

- `stop`: Stop the current broadcast.  
    - Usage: `botwave> stop`

- `list`: List files in the specified directory (default: upload directory).  
    - Usage: `botwave> list [directory]`

- `upload`: Upload a file to the upload directory.  
    - Usage: `botwave> upload <source> <destination>`

- `handlers`: List all handlers or commands in a specific handler file.  
    - Usage: `botwave> handlers [filename]`

- `>`: Run a shell command on the main OS.  
    - Usage: `botwave> < <command>`

- `help`: Display the help message.  
    - Usage: `botwave> help`

- `exit`: Exit the application.  
    - Usage: `botwave> exit`

### Supported handlers
- `l_onready`: When the client is ready (on startup).
- `l_onstart`: When a broadcast has been start.
- `l_onstop`: When a broadcast has been stopped (manually).

Check [misc_doc/handlers.md](/misc_doc/handlers.md) for a better documentation.

---

![A DPIP Studio Project](https://madeby.dpip.lol)

![Made by Douxx](https://madeby.douxx.tech)