<div align="center">

<img src="https://togp.douxx.tech/?repo=botwave&owner=dpipstudio&cache=false&svg=https://raw.githubusercontent.com/dpipstudio/botwave/refs/heads/main/assets/readme_assets/togp_logo.svg&failurl=https://images.dpip.lol/bw-logo-big.png" alt="BotWave"/>

<h1>BotWave - Your Raspberry Pi FM Network</h1>
<h4> <a href="https://botwave.dpip.lol">Website</a> | <a href="#installation">Install</a> | <a href="#mentions">Mentions</a> | <a href="https://github.com/dpipstudio/botwave/wiki">Wiki</a></h4>

</div>

BotWave lets you broadcast audio over FM radio using Raspberry Pi devices. It supports both single-device setups and multi-Pi networks, with features like remote control, live streaming, automated actions, and more, making it great for learning, experimentation, and creative projects.

<details>
<summary><strong>Table of Contents</strong></summary>
<hr>
<ul>
<li><a href="#features">Features</a></li>

<li>
<a href="#requirements">Requirements</a>
<ul>
<li><a href="#server">Server</a></li>
<li><a href="#client">Client</a></li>
</ul>
</li>

<li>
<a href="#get-started">Get Started</a>
<ul>
<li><a href="#installation">Installation</a></li>

<li>
<a href="#using-the-local-client-single-pi">Using The Local Client (Single Pi)</a>
<ul>
<li><a href="#1-starting-the-local-client">Starting the local client</a></li>
<li><a href="#2-understanding-the-local-client-command-line-interface">Understanding the local client command line interface</a></li>
<li><a href="#3-uploading-files-to-the-local-client">Uploading files to the local client</a></li>
<li><a href="#4-starting-a-broadcast">Starting a broadcast</a></li>
<li><a href="#5-stopping-a-broadcast">Stopping a broadcast</a></li>
<li><a href="#6-exiting-properly">Exiting properly</a></li>
</ul>
</li>

<li>
<a href="#using-the-client-server-multiple-pis">Using The Client-Server (Multiple Pis)</a>
<ul>
<li><a href="#1-connect-the-client-and-the-server-together">Connect the client and the server together</a></li>
<li><a href="#2-understanding-the-server-command-line-interface">Understanding the server command line interface</a></li>
<li><a href="#3-uploading-files-to-the-client">Uploading files to the client</a></li>
<li><a href="#4-starting-a-broadcast-1">Starting a broadcast</a></li>
<li><a href="#5-stopping-a-broadcast-1">Stopping a broadcast</a></li>
<li><a href="#6-exiting-properly-1">Exiting properly</a></li>
</ul>
</li>

</ul>
</li>

<li><a href="#remote-management">Remote Management</a></li>
<li><a href="#advanced-usage">Advanced Usage</a></li>
<li><a href="#updating-botwave">Updating BotWave</a></li>
<li><a href="#uninstallation">Uninstallation</a></li>
<li><a href="#botwave-server-for-cloud-instances">BotWave Server For Cloud Instances</a></li>
<li><a href="#get-help">Get Help</a></li>
<li><a href="#mentions">Mentions</a></li>
<li><a href="#license">License</a></li>
<li><a href="#credits">Credits</a></li>
</ul>
<hr>
</details>


## Features

- **Standalone Client**: Run a single Raspberry Pi independently, no server needed.
- **Server-Client Architecture**: Manage multiple Raspberry Pi clients from a central server.
- **Audio Broadcasting**: Broadcast audio files over FM radio. Supports MP3, WAV, FLAC, AAC, and more. Files are converted automatically.
- **File Upload**: Upload audio files to clients for broadcasting.
- **Remote Management**: Start, stop, and manage broadcasts remotely.
- **Authentication**: Client-server authentication with passkeys.
- **Protocol Versioning**: Ensure compatibility between server and clients.
- **Live Broadcasting**: Stream live output from any application in real time.
- **Queue System**: Manage playlists and multiple audio files at once.
- **Task Automation**: Run commands automatically on events and start on system boot.

## Requirements
> All requirements can be installed automatically via the installer, see below.

### Server
- Python >= 3.9

### Client
- Raspberry Pi (models 2, 3, 4, or Zero. **Pi 5 and Pico are not supported**)
- Root access
- Python >= 3.9
- [bw_custom](https://github.com/dpipstudio/bw_custom)
- (Wire or antenna connected to GPIO 4 / pin 7)


## Get Started

> [!NOTE]
> For a more detailed setup guide, check [`/wiki/Setup`](https://github.com/dpipstudio/botwave/wiki/Setup)

> [!WARNING]
> - **BotWave broadcasts FM signals**, which may be regulated in your area.
> - **Check local laws** before use. Unauthorized broadcasts may incur fines.
> - **Use a band-pass filter** to minimize interference with other services.
> - **The authors are not responsible** for legal issues or hardware damage.
> - **See FAQ** for more information: [`/wiki/FAQ`](https://github.com/dpipstudio/botwave/wiki/FAQ)

### Installation

For Debian-based systems (Raspberry Pi OS, Ubuntu, Zorin OS, etc.), we provide an install script:
```sh
curl -sSL https://botwave.dpip.lol/install | sudo bash
```

If you'd like to review the script before running it:
```sh
curl -sSL https://botwave.dpip.lol/install -o bw_install.sh
cat bw_install.sh
sudo bash bw_install.sh
```

> `sudo` is required for system-wide installation. BotWave installs to `/opt/BotWave` with binary symlinks in `/usr/local/bin`.

**During installation, you'll be asked a few questions:**

- **Installation type**: If you have a single Raspberry Pi, choose **Client**. If you also want to run a server on the same machine, choose **Both**. Other devices will only be able to run the **Server**.
- **ALSA loopback card**: This is only needed if you plan to do **live broadcasting** (streaming audio in real time). If you're just playing audio files, you can skip it. You can always enable it later with `--alsa`.

<details>
<summary><code>Installer options</code></summary>
<hr>
<pre>
Usage: curl -sSL https://botwave.dpip.lol/install | sudo bash [-s -- [MODE] [OPTIONS]]

Modes:
  client              Install client components
  server              Install server components
  both                Install both client and server components

Options:
  -l, --latest        Install from the latest commit (even if unreleased)
  -t, --to &lt;version&gt;  Install a specific release version
  -b, --branch &lt;name&gt; Install from a specific branch (default: main)
  --[no-]alsa         Setup ALSA loopback card
  -h, --help          Show this help message
</pre>
<p>Adding <code>-s -- &lt;server, client or both&gt; --alsa</code> at the end of the command skips the interactive menu and goes straight to installation.</p>
<p>Note that all this is optional and not needed for basic installation.</p>
<hr>
</details>

---

> [!TIP]
> **Not sure which mode to pick?**
> - **One Raspberry Pi**: use the **Local Client** (no server needed). Jump to [Using The Local Client](#using-the-local-client-single-pi).
> - **Multiple Raspberry Pis**: use the **Client-Server** setup. Jump to [Using The Client-Server](#using-the-client-server-multiple-pis).

---

### Using The Local Client (Single Pi)

The local client runs entirely on one Raspberry Pi. So no server or second machine required. This is the recommended starting point if you're new to BotWave.

#### 1. Starting the local client
```sh
sudo bw-local
```

<details>
<summary><code>Local client options</code></summary>
<hr>
<pre>
Usage: sudo bw-local [OPTIONS]

sudo bw-local [-h] [--upload-dir UPLOAD_DIR] [--handlers-dir HANDLERS_DIR]
                [--skip-checks] [--daemon] [--ws WS] [--pk PK]

options:
  -h, --help            show this help message and exit
  --upload-dir UPLOAD_DIR
                        Directory to store uploaded files
  --handlers-dir HANDLERS_DIR
                        Directory to retrieve l_ handlers from
  --skip-checks         Skip system requirements checks
  --daemon              Run in daemon mode (non-interactive)
  --ws WS               WebSocket port for remote control
  --pk PK               Optional passkey for WebSocket authentication
</pre>
<hr>
</details>

<details>
<summary><code>Hardware setup</code></summary>
<hr>
<p>To broadcast, connect a wire or antenna to <strong>GPIO 4 (pin 7)</strong> on your Raspberry Pi. Even a short bare wire improves range significantly over nothing.</p>
<div align="center">
<img src="/assets/readme_assets/gpio.png" alt="GPIO diagram" width="300"/>
<img src="/assets/readme_assets/example_gpio.jpg" alt="Example wiring" width="300"/>
</div>
<hr>
</details>

#### 2. Understanding the local client command line interface
The local client has a CLI to manage it. Type `help` for a list of all available commands.

#### 3. Getting audio files onto the local client

BotWave supports most common audio formats (MP3, WAV, FLAC, AAC, OGG, and more). Files are converted to WAV automatically when needed.

You have two options to get files onto your Pi:

**Option A: Download a file from a URL:**
```sh
botwave> dl https://cdn.douxx.tech/files/ss.wav
```

**Option B: Upload a file already on the Pi's filesystem:**

> [!NOTE]
> If you need to transfer a file from your personal computer to the Pi first, use `scp` from your computer:
> ```sh
> scp mysong.mp3 pi@<pi-ip-address>:/home/pi/
> ```
> Then inside BotWave:

```sh
botwave> upload /home/pi/mysong.mp3        # a single file

botwave> upload /home/pi/music/            # every supported file in a folder
```

#### 4. Starting a broadcast
```sh
botwave> start ss.wav 88    # broadcasts ss.wav at 88 MHz
```

#### 5. Stopping a broadcast
```sh
botwave> stop
```

#### 6. Exiting properly
```sh
botwave> exit    # cleans up and exits
```

---

### Using The Client-Server (Multiple Pis)

This setup lets you manage a network of Raspberry Pis from a central server. It assumes you have one machine with the `server` component installed and at least one Raspberry Pi with the `client` component installed, both on the same network.

#### 1. Connect the client and the server together

Start the `server` on your server machine:
```sh
bw-server
```

<details>
<summary><code>Server options</code></summary>
<hr>
<pre>
Usage: bw-server [OPTIONS]

bw-server [-h] [--host HOST] [--port PORT] [--fport FPORT] [--pk PK]
                 [--handlers-dir HANDLERS_DIR] [--start-asap] [--ws WS]
                 [--daemon]

options:
  -h, --help            show this help message and exit
  --host HOST           Server host
  --port PORT           Server port
  --fport FPORT         File transfer (HTTP) port
  --pk PK               Passkey for authentication
  --handlers-dir HANDLERS_DIR
                        Directory to retrieve s_ handlers from
  --start-asap          Start broadcasts immediately (may cause client desync)
  --ws WS               WebSocket port for remote shell access
  --daemon              Run in non-interactive daemon mode
</pre>
<hr>
</details>

Then, on the Raspberry Pi, connect it to the server:

> If you don't know your server's IP address, run `< hostname -I` in the BotWave shell.

```sh
sudo bw-client 192.168.1.10    # replace with your server's IP
```

> `sudo` is required to access Raspberry Pi hardware.

<details>
<summary><code>Client options</code></summary>
<hr>
<pre>
Usage: sudo bw-client [OPTIONS]

sudo bw-client [-h] [--port PORT] [--fhost FHOST] [--fport FPORT]
                 [--upload-dir UPLOAD_DIR] [--pk PK] [--skip-checks]
                 [server_host]

positional arguments:
  server_host           Server hostname/IP

options:
  -h, --help            show this help message and exit
  --port PORT           Server port
  --fhost FHOST         File transfer server hostname/IP (defaults to server_host)
  --fport FPORT         File transfer (HTTP) port
  --upload-dir UPLOAD_DIR
                        Uploads directory
  --pk PK               Passkey for authentication
  --skip-checks         Skip update and requirements checks
</pre>
<hr>
</details>

<details>
<summary><code>Hardware setup</code></summary>
<hr>
<p>To broadcast, connect a wire or antenna to <strong>GPIO 4 (pin 7)</strong> on your Raspberry Pi. Even a short bare wire improves range significantly over nothing.</p>
<div align="center">
<img src="/assets/readme_assets/gpio.png" alt="GPIO diagram" width="300"/>
<img src="/assets/readme_assets/example_gpio.jpg" alt="Example wiring" width="300"/>
</div>
<hr>
</details>

If the connection succeeds, you'll see a message confirming that `<pi-hostname>_<pi-ip>` has connected.

#### 2. Understanding the server command line interface
The server has a CLI to manage it. Type `help` for a list of all available commands.

When targeting clients, you can use:
- The client ID: `raspberry_192.168.1.11`
- The client hostname: `raspberry`
- Multiple clients: `raspberry,raspberry2`
- All connected clients: `all`

#### 3. Uploading files to the client

BotWave supports most common audio formats (MP3, WAV, FLAC, AAC, OGG, and more). Files are converted automatically when needed.

**Option A: Upload a file stored on the server machine:**
```sh
botwave> upload all /home/server/Downloads/ss.wav       # a single file

botwave> upload all /home/server/Downloads/bw_files/    # every supported file in a folder
```

**Option B: Have the client download from a URL directly:**
```sh
botwave> dl all https://cdn.douxx.tech/files/ss.wav
```

#### 4. Starting a broadcast
```sh
botwave> start all ss.wav 88    # broadcasts ss.wav at 88 MHz to all clients
```

#### 5. Stopping a broadcast
```sh
botwave> stop all
```

#### 6. Exiting properly
```sh
botwave> exit    # kicks all clients and shuts down the server cleanly
```

---

## Remote Management
BotWave lets you manage your server or local client remotely via WebSocket. We recommend using [`BWSC`](https://github.com/douxxtech/bwsc) for this.

#### 1. Install BWSC
```sh
npm i -g bwsc
```

#### 2. Enable remote access on your server or local client

Add the `--ws` flag when starting BotWave. A passkey is strongly recommended if exposed to the internet:

```sh
bw-server --ws 9939 --pk 1234       # for the server component

bw-local --ws 9939 --pk 1234        # for the local client component
```

> If you add a passkey to the server, also pass it to connecting clients: `sudo bw-client <server-ip> --pk <passkey>`

#### 3. Connect remotely
```sh
bwsc 192.168.1.10 1234    # replace with your server IP and passkey
```

#### 4. Manage remotely
You'll now have access to the full server or local client CLI remotely.
Note that the `<`, `|`, and `exit` commands are not available via remote shell.

```sh
botwave> help
```

## Advanced Usage
For more detailed documentation, check the following resources:
- **Server help**: [`/server/server.md`](/server/server.md)
- **Client help**: [`/client/client.md`](/client/client.md)
- **Local client help**: [`/local/local.md`](/local/local.md)
- **AutoRun help**: [`/autorun/autorun.md`](/autorun/autorun.md)
- **Automated actions**: [`/misc_doc/handlers.md`](/misc_doc/handlers.md), [`Main/Automate Your Setup`](https://github.com/dpipstudio/botwave/wiki/Automate-your-setup)
- **Remote management protocol**: [`/misc_doc/websocket.md`](/misc_doc/websocket.md)

### Updating BotWave
```bash
sudo bw-update
```

### Uninstallation
```bash
curl -sSL https://botwave.dpip.lol/uninstall | sudo bash
```

> [!WARNING]
> This will delete `/opt/BotWave/`. Back up any important files (handlers, uploads) before uninstalling.

### BotWave Server For Cloud Instances
You can try the BotWave server directly on cloud platforms:

[![Run in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/open?cloudshell_git_repo=https://github.com/dpipstudio/botwave&cloudshell_tutorial=misc_doc/google-shell.md&show=terminal)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dpipstudio/botwave)


### Get Help
Got a question or an issue?
- Open an [issue](https://github.com/dpipstudio/botwave/issues/new)
- Join the [Discord](https://discord.gg/r5ragNsQxp)


## Mentions
**BotWave mentions**: Here are some posts that talk about BotWave. Thanks to their creators!
<div align="center">
<a href="https://tom-doerr.github.io/repo_posts/" target="_blank"><img src="assets/readme_assets/badge_repository_showcase.svg" alt="tom-doerr"/></a>
<a href="https://peppe8o.com/?s=botwave" target="_blank"><img src="assets/readme_assets/badge_peppe8o.svg" alt="peppe8o"/></a>
<a href="https://hn.algolia.com/?dateRange=all&page=0&prefix=true&query=botwave%20radio&sort=byDate&type=all" target="_blank"><img src="assets/readme_assets/badge_hacker_news.svg" alt="show hn"/></a>
<a href="https://korben.info/botwave-raspberry-pi-emetteur-fm-radio.html" target="_blank"><img src="assets/readme_assets/badge_le_site_de_korben.svg" alt="le site de korben"/></a>
<a href="https://www.cyberplanete.net/raspberry-pi-radio-botwave/" target="_blank"><img src="assets/readme_assets/badge_cyberplanete.svg" alt="cyberplanete"/></a>
</div>

## Supports
**BotWave is supported by donations** from the following people and projects.
Your contributions help with development, hosting, and hardware costs 🙏
<div align="center">
<a href="https://vocal.wtf" target="_blank"><img src="assets/readme_assets/badge_vocal.svg" alt="vocal"/></a>
</div>

## License
BotWave is licensed under [GPLv3.0](LICENSE).

## Credits

![a DPIP Studio Project](https://madeby.dpip.lol)
![Made by Douxx](https://madeby.douxx.tech)