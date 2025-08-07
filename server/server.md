# BotWave - Server | Documentation

> This tool is included in the **CLIENT** install.

BotWave Server is a program designed to manage multiple BotWave clients, allowing for the upload and broadcast of audio files over FM radio using Raspberry Pi devices.

## Requirements
* Python 3.x

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions and knowledge of the regulations before using BotWave for broadcasting purposes.


We highly recommand using the official installer (Check the [main README](/README.md)) -- If you don't want to or are not using a Linux distribution, find how to install it by yourself. (Tip: on windows, use wsl)

## Usage
To start the BotWave Server, use the following command:

```bash
sudo bw-server [--host HOST] [--port PORT] [--pk PASSKEY] [--ws PORT] [--skip-update-check] [--start-asap] [--daemon]
```

### Arguments
* `--host`: The host address to bind the server to (default: 0.0.0.0).
* `--port`: The port on which the server will listen (default: 9938).
* `--pk`: Optional passkey for client authentication.
* `--ws`: Port for the WebSocket server. You can connect remotly to your websocket server via [botwave.dpip.lol](https://botwave.dpip.lol/websocket/). For an API documentation, check [misc_doc/websocket.md](/misc_doc/websocket.md)
* `--skip-update-check`: Skip checking for protocol updates.
* `--start-asap`: Starts broadcasting as soon as possible. Can cause delay between different clients broadcasts.
* `--daemon`: Run in daemon mode (non-interactive, requires --ws port).

### Example
```bash
sudo bw-client --host 0.0.0.0 --port 9938 --pk mypasskey
```

## Commands available

`list`: Lists all connected clients.  
    - Usage: `botwave> list`  

`upload`: Upload a file to specified client(s).  
    - Usage: `botwave> upload <targets> <path/of/file.wav>`  

`dl`: Downloads a file from an external URL.  
    - Usage: `botwave> dl <targets> <url>`

`start`: Starts broadcasting on specified client(s).  
    - Usage: `botwave> start <targets> <file> [freq] [ps] [rt] [pi] [loop]`  

`stop`: Stops broadcasting on specified client(s).  
    - Usage: `botwave> stop <targets>`  

`kick`: Kicks specified client(s) from the server.  
    - Usage: `botwave> kick <targets> [reason]`  

`restart`: Restarts specified client(s).  
    - Usage: `botwave> restart <targets>`  

`handlers`: List all handlers or commands in a specific handler file.  
    - Usage: `botwave> handlers [filename]`

`>`: Run a shell command on the main OS.  
    - Usage: `botwave> < <command>`

`exit`: Stops and exit the BotWave server.  
    - Usage: `botwave> exit`  

`help`: Shows the help.  
    - Usage: `botwave> help`  

```
targets: Specifies the target clients. Can be 'all', a client ID, a hostname, or a comma-separated list of clients (client1,client2,etc).
```

### Supported handlers
- `s_onready`: When the server is ready (on startup).
- `s_onstart`: When a broadcast has been start.
- `s_onstop`: When a broadcast has been stopped (manually).
- `s_onconnect`: When a client connects to the server.
- `s_ondisconnect`: When a client disconnects form the server.
- `s_onwsjoin`: When a websocket client joins the server.
- `s_onwsleave`: When a websocket client leaves the server (buggy).

Check [misc_doc/handlers.md](/misc_doc/handlers.md) for a better documentation.

---

![a DPIP Studio Project](https://madeby.dpip.lol)
![Made by Douxx](https://madeby.douxx.tech)
