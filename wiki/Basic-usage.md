In this page are documented the basics of BotWave, along with some additional tips.

> [!NOTE]
> This page assumes you've already installed BotWave and have your setup running. If not, please follow [Base/Setup](https://github.com/dpipstudio/botwave/wiki/Setup) first.

BotWave is controlled through a command-line interface (CLI). Once BotWave is running, you'll see a `botwave >` prompt where you type commands. Each command follows a simple structure:

```
command <required_argument> [optional_argument]
```

- `<angle brackets>` mean the argument is **required**
- `[square brackets]` mean the argument is **optional**

That's all you need to know for now. Let's get broadcasting.

> [!NOTE]
> If you're using the **local client** (`bw-local`), commands work almost identically, except you don't need to specify targets. there's only one device. So `stop all` becomes just `stop`, `dl all` becomes just `dl`, and so on.


## Command line options

Before starting BotWave, you can configure it with flags. Here are the supported options for each component:

### Server
```bash
bw-server [-h] [--host HOST] [--port PORT] [--fport FPORT] [--pk PK] [--handlers-dir HANDLERS_DIR] [--start-asap | --no-start-asap] [--skip-checks | --no-skip-checks] [--rc RC] [--talk | --no-talk] [--config CONFIG] [--daemon | --no-daemon]
```

| Argument       | Default   | Description                                        |
|--|--|--|
| `--host`       | 0.0.0.0   | Host address to bind the server to                 |
| `--port`       | 9938      | Port for the command/control channel               |
| `--fport`      | 9921      | Port for the file transfer server                  |
| `--pk`         | None      | Passkey for client authentication                  |
| `--rc`         | None      | Enable remote shell access on this port            |
| `--start-asap` | False     | Start broadcasts immediately (may cause desync)    |
| `--skip-checks`| False     | Skip update checks                                 |
| `--talk`       | False     | Show debug logs                                    |
| `--daemon`     | False     | Run in non-interactive daemon mode                 |
| `--config`     | None      | Path to a config file to load into environment     |

### Client
```bash
sudo bw-client [-h] [--port PORT] [--fhost FHOST] [--fport FPORT] [--upload-dir UPLOAD_DIR] [--pk PK] [--skip-checks | --no-skip-checks] [--talk | --no-talk] [--config CONFIG] [server_host]
```

| Argument        | Default                  | Description                                       |
|--|--|-|
| `server_host`   | (prompted)               | Hostname or IP of the BotWave server              |
| `--port`        | 9938                     | Port for the server connection                    |
| `--fport`       | 9921                     | Port for file transfers                           |
| `--upload-dir`  | /opt/BotWave/uploads     | Directory to store received files                 |
| `--pk`          | None                     | Passkey for server authentication                 |
| `--skip-checks` | False                    | Skip system requirements checks                   |
| `--talk`        | False                    | Show debug logs                            |
| `--config`      | None                     | Path to a config file to load into environment    |

### Local client
```bash
sudo bw-local [-h] [--upload-dir UPLOAD_DIR] [--handlers-dir HANDLERS_DIR] [--skip-checks | --no-skip-checks] [--daemon | --no-daemon] [--rc RC] [--pk PK] [--talk | --no-talk] [--config CONFIG]
```

| Argument         | Default                  | Description                                     |
|--|--|--|
| `--upload-dir`   | /opt/BotWave/uploads     | Directory containing broadcastable files        |
| `--handlers-dir` | /opt/BotWave/handlers    | Directory containing handler files              |
| `--skip-checks`  | False                    | Skip system requirements checks                 |
| `--daemon`       | False                    | Run in non-interactive daemon mode              |
| `--rc`           | None                     | Enable remote shell access on this port         |
| `--pk`           | None                     | Passkey for WebSocket authentication            |
| `--talk`         | False                    | Show debug logs                          |
| `--config`       | None                     | Path to a config file to load into environment  |


## Basic Commands

For this tutorial we'll use the following setup:
- **Server**: `bw-server --pk YouSh0uldStarBW --start-asap`
- **Client**: `sudo bw-client botwave.dpip.lol --pk YouSh0uldStarBW --skip-checks`

Once both are running and connected, you're ready to go. Type `help` at any time to see the full list of available commands.


### 1. list: See connected clients

The `list` command shows all clients currently connected to your server, along with some basic info about each one. It's a good habit to run this first to confirm everything is connected properly.

```
botwave> list
```

<details>
<summary><code>Expected result</code></summary>
<hr>
<pre>
botwave › list
 Connected Clients ──────────────────

ID: botwave-client_192.168.1.96
  Hostname: botwave-client
  Machine: aarch64
  System: Linux
  Protocol Version: 2.0.0
  Connected: 2025-11-26 23:04:30
  Last seen: 2025-11-26 23:04:30
</pre>
<hr>
</details>

> [!TIP]
> When running commands that target clients, you can use:
> - `all`: every connected client
> - `raspberry`: a client by hostname
> - `raspberry_192.168.1.11`: a client by full ID
> - `raspberry,raspberry2`: multiple clients at once



### 2. lf: List files on a client

Before broadcasting, you need audio files on your client. The `lf` command shows what's already there.

```
botwave> lf all
```

<details>
<summary><code>Expected result</code></summary>
<hr>
<pre>
botwave › lf all
[INFO] Listing files from 1 client(s)
[OK]   botwave-client (botwave-client_192.168.1.96): 0 file(s)
    No files found
</pre>
<hr>
</details>

Fresh install, no files yet. That's expected, so lset's fix that.



### 3. dl: Download a file onto the client

The `dl` command tells your client to download a file directly from a URL. This is the quickest way to get audio onto your Pi without manually transferring files.

BotWave supports most common audio formats (MP3, WAV, FLAC, AAC, OGG, and more). Files are converted automatically if needed.

```
botwave> dl all https://cdn.douxx.tech/files/ss.wav
```

<details>
<summary><code>Expected result</code></summary>
<hr>
<pre>
botwave › dl all https://cdn.douxx.tech/files/ss.wav
[BCAST] Requesting download from 1 client(s)...
[FILE]   botwave-client (botwave-client_192.168.1.96): Download request sent

[OK] botwave-client (botwave-client_192.168.1.96): Downloaded ss.wav
</pre>
<hr>
</details>

Run `lf all` again and you should now see `ss.wav` listed.

> [!TIP]
> If you want to upload a file that's already on your server machine instead, use the `upload` command:
> ```
> botwave> upload all /home/server/Downloads/mysong.mp3
> ```
> Need to transfer a file from your personal computer to the Pi first? Use `scp` from your computer's terminal:
> ```bash
> scp mysong.mp3 pi@<pi-ip-address>:/home/pi/
> ```



### 4. start: Begin broadcasting

The `start` command tells your client to transmit a file over FM. Think of it as: *"which clients should broadcast what, and how?"*

```
botwave> start <targets> <file> [frequency] [loop] [PS] [RT] [PI]
```

| Argument    | Description |
|--|--|
| `targets`   | Which clients to broadcast on (`all`, `pi1`, `pi1,pi2`) |
| `file`      | The file to broadcast (must already be on the client) |
| `frequency` | FM frequency in MHz, default `90.0`, range `76.0–108.0` |
| `loop`      | Repeat continuously (`true` or `false`, default `false`) |
| `PS`        | Station name shown on RDS-capable radios (max 8 characters) |
| `RT`        | Station description shown on RDS-capable radios (max 64 characters) |
| `PI`        | Program Identifier code (optional, for advanced RDS setups) |

> Don't worry about PS, RT, and PI for now. they're optional extras that make your broadcast show up nicely on radios that support RDS. You don't need them to get started.

Let's broadcast `ss.wav` on 88.5 MHz and loop it:

```
botwave> start all ss.wav 88.5 true
```

<details>
<summary><code>Expected result</code></summary>
<hr>
<pre>
botwave › start all ss.wav 88.5 true
[BCAST] Starting broadcast ASAP
[BCAST] Starting broadcast on 1 client(s)...
[OK]   botwave-client (botwave-client_192.168.1.96): START command sent
[BCAST] Broadcast start commands sent: 1/1

[OK] botwave-client (botwave-client_192.168.1.96): Broadcasting started
</pre>
<hr>
</details>

If everything worked, tune a radio to 88.5 MHz. You should hear your broadcast!

> [!TIP]
> Once you're comfortable, you can experiment with:
> - Changing the frequency: `start all ss.wav 95`
> - Adding a station name: `start all ss.wav 95 false MyRadio`
> - Adding a description: `start all ss.wav 95 false MyRadio "Hello listeners!"`


### 5. stop: Stop broadcasting

```
botwave> stop all
```

<details>
<summary><code>Expected result</code></summary>
<hr>
<pre>
botwave › stop all
[OK]   botwave-client (botwave-client_192.168.1.96): STOP command sent
[BCAST] Broadcast stop commands sent: 1/1

[OK] botwave-client (botwave-client_192.168.1.96): Broadcast stopped
</pre>
<hr>
</details>



### 6. exit: Shut down cleanly

The `exit` command kicks all connected clients and shuts the server down properly. Always prefer this over just closing the terminal, since it ensures everything disconnects cleanly.

```
botwave> exit
```

<details>
<summary><code>Expected result</code></summary>
<hr>
<pre>
botwave › exit
[SERVER] Shutting down server...
[CLIENT] Kicking 1 client(s)...
[OK]   botwave-client (botwave-client_192.168.1.96): Kicked - Server is shutting down
[CLIENT] Kick completed
[SERVER] Main socket stopped
[SERVER] File transfer (HTTP) server stopped
[OK] Server shutdown complete
</pre>
<hr>
</details>



You now know the basics of BotWave. From here, explore the rest of the wiki at your own pace:
- **[Main/Queue System](https://github.com/dpipstudio/botwave/wiki/Queue-system)**: play multiple files in sequence automatically
- **[Main/Live Broadcasting](https://github.com/dpipstudio/botwave/wiki/Live-broadcasting)**: stream live audio in real time
- **[Main/Automate Your Setup](https://github.com/dpipstudio/botwave/wiki/Automate-your-setup)**: start on boot and automate actions