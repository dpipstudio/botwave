<div align="center">

<img src="https://togp.xyz/?repo=botwave&owner=dpipstudio&cache=false&svg=https://raw.githubusercontent.com/dpipstudio/botwave/refs/heads/main/assets/readme_assets/togp_logo.svg&failurl=https://images.dpip.lol/bw-logo-big.png" alt="BotWave"/>

<h1>BotWave - Your Raspberry Pi FM Network</h1>
<h4> <a href="https://botwave.dpip.lol">Website</a> | <a href="#installation">Install</a> | <a href="#mentions">Mentions</a> </h4>


</div>

BotWave lets you broadcast audio over FM radio using Raspberry Pi devices. It supports server-client management, remote control, automated actions, live streaming, and more. That makes it ideal for learning, experimentation, and creative projects.

<details>
<summary><strong>Table of Contents</strong></summary>

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
<a href="#using-the-client-server">Using The Client-Server</a>
<ul>
<li><a href="#1-connect-the-client-and-the-server-together">Connect the client and the server together</a></li>
<li><a href="#2-understanding-the-server-command-line-interface">Understanding the server command line interface</a></li>
<li><a href="#3-uploading-files-to-the-client">Uploading files to the client</a></li>
<li><a href="#4-starting-a-broadcast">Starting a broadcast</a></li>
<li><a href="#5-stopping-a-broadcast">Stopping a broadcast</a></li>
<li><a href="#6-exiting-properly">Exiting properly</a></li>
</ul>
</li>

<li>
<a href="#using-the-local-client">Using The Local Client</a>
<ul>
<li><a href="#1-starting-the-local-client">Starting the local client</a></li>
<li><a href="#2-understanding-the-local-client-command-line-interface">Understanding the local client command line interface</a></li>
<li><a href="#3-uploading-files-to-the-local-client">Uploading files to the local client</a></li>
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
<li><a href="#mentions">Mentions</a></li>
<li><a href="#license">License</a></li>
<li><a href="#credits">Credits</a></li>
</ul>
</details>


## Features

- **Server-Client Architecture**: Manage multiple Raspberry Pi clients from a central server.
- **Audio Broadcasting**: Broadcast audio files over FM radio.
- **File Upload**: Upload audio files to clients for broadcasting.
- **Remote Management**: Start, stop, and manage broadcasts remotely.
- **Authentication**: Client-server authentication with passkeys.
- **Protocol Versioning**: Ensure compatibility between server and clients.
- **Live Broadcasting**: Stream live output from any application in real time. (Still in development, see [`#24`](https://github.com/dpipstudio/botwave/issues/24))

## Requirements
> All requirements can be installed automatically via the installer, see below.

### Server
- Python >= 3.9

### Client
- Raspberry Pi
- Root access
- Python >= 3.9
- [bw_custom](https://github.com/dpipstudio/bw_custom)
- (Wire or antenna)


## Get Started

> [!NOTE]
> If you want a more detailed guide, you might want to check [`/wiki/Setup`](https://github.com/dpipstudio/botwave/wiki/Setup)

> [!WARNING]
> - **BotWave broadcasts FM signals**, which may be regulated in your area.
> - **Check local laws** before use, unauthorized broadcasts may incur fines.
> - **Use a band-pass filter** to minimize interference.
> - **The authors are not responsible** for legal issues or hardware damage.
> - **See FAQ** for more information: [`/wiki/FAQ`](https://github.com/dpipstudio/botwave/wiki/FAQ)

### Installation
For debian-like operating systems (Debian, Ubuntu, Raspberry Pi OS, Zorin OS, etc), we provide an install script.
```sh
curl -sSL https://botwave.dpip.lol/install | sudo bash
```

If you wish to review the script before running it, run the following commands:

```sh
curl -sSL https://botwave.dpip.lol/install -o bw_install.sh
cat bw_install.sh
sudo bash bw_install.sh
```
> `sudo` is required to access system-wide access. We use it to install BotWave into `/opt/BotWave` and binary symlinks into `/usr/local/bin`.  
> If you're working on an OS that isn't debian-like, you can either try to tweak our install script, or you can open an issue to get help.

<details>
<summary><code>Installer options</code></summary>
<p></p>
<pre>
Usage: curl -sSL https://botwave.dpip.lol/install | sudo bash [-s -- [MODE] [OPTIONS]]

Modes:
  client              Install client components
  server              Install server components
  both                Install both client and server components

Options:
  -l, --latest        Install from the latest commit (even if unreleased)
  -t, --to &lt;version&gt;  Install a specific release version
  -h, --help          Show this help message
</pre>
<p>Adding <code> -s &lt;server, client or both&gt;</code> at the end of the command skips the interactive menu and goes straight to installation.</p>
<p>Use <code> -s -- &lt;server, client or both&gt; &lt;options&gt;</code> to add options flags.</p>
<p>Note that all this is optional and not needed for basic installation.</p>
</details>

> [!TIP]
> If you plan to only use one raspberry pi (not a network of them), we offer a standalone client, that allows you to use BotWave without a server. If you wish to use the "local client", go to [`Using The Local Client`](#using-the-local-client).

### Using The Client-Server
In those examples, it is assumed that you have one machine with the `server` component installed, and one Raspberry Pi with the `client` component installed. It is also assumed that both are on the same network. 

#### 1. Connect the client and the server together
Start by starting the `server`
```sh
bw-server
```

<details>
<summary><code>Server options</code></summary>
<p></p>
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
  --start-asap          Start broadcasts immediately (may cause client
                        desync)
  --ws WS               WebSocket port for remote shell access
  --daemon              Run in non-interactive daemon mode
</pre>
</details>

Once you got your server running, run the `client` specifying the server IP:
> If you don't know your server IP, run `< hostname -I` in the BotWave shell input.

```sh
sudo bw-client 192.168.1.10 # assuming that the server ip is the following
```

> `sudo` is used to access the Raspberry Pi hardware and filesystem.

<details>
<summary><code>Client options</code></summary>
<p></p>
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
  --fhost FHOST         File transfer server hostname/IP (defaults to
                        server_host)
  --fport FPORT         File transfer (HTTP) port
  --upload-dir UPLOAD_DIR
                        Uploads directory
  --pk PK               Passkey for authentication
  --skip-checks         Skip update and requirements checks
</pre>
</details>

<details>
<summary><code>Hardware installation for clients</code></summary>
<p></p>
<p>To use BotWave Client for broadcasting, you need to set up the hardware correctly. This involves eventually connecting an antenna or a cable to the Raspberry Pi's GPIO 4 (pin 7).</p>
<img src="/assets/readme_assets/gpio.png"/>
<img src="/assets/readme_assets/example_gpio.jpg"/>

</details>

If everything went well, you should see a message telling that `<pi hostname>_<pi ip>` successfully connected.

#### 2. Understanding the server command line interface
The `server` has a CLI to manage it. Write `help` for a list of all commands available.  
When performing an action on `clients`, you will need to specify the target(s). Those can be:
- The `client` ID, eg: `raspberry_192.168.1.11`
- The `client` hostname, eg: `raspberry`
- Multiple clients, eg: `raspberry,raspberry2`
- Every connected client: `all`


#### 3. Uploading files to the client
BotWave needs each Pi of the network to locally have the `wave` (`.wav`) file, this is mainly to improve bandwidth usage. To upload a file, you have two options:

**1. Upload a file stored on the server machine:** 
```sh
botwave> upload all /home/server/Downloads/ss.wav # a single file

botwave> upload all /home/server/Downloads/bw_files/ # every .wav file in the given folder
```

**2. Upload a file stored on an external server:**
```sh
botwave> dl all https://cdn.douxx.tech/files/ss.wav # download the file from cdn.douxx.tech
```

#### 4. Starting a broadcast
```sh
botwave> start all ss.wav 88 # this broadcasts the file ss.wav on 88MHz
```

#### 5. Stopping a broadcast
```sh
botwave> stop all
```

#### 6. Exiting properly
```sh
botwave> exit # this kicks (stops) all clients and cleans up the server properly
```

### Using The Local Client
The `local client` is a standalone tool that doesn't require a server. You can run it and directly access the CLI interface. This part assumes that you have a Raspberry Pi with the `client` installed.

#### 1. Starting the local client
To start the local client, run the following command:
```sh
sudo bw-local
```

<details>
<summary><code>Local client options</code></summary>
<p></p>
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
</details>

<details>
<summary><code>Hardware installation for clients</code></summary>
<p></p>
<p>To use BotWave Client for broadcasting, you need to set up the hardware correctly. This involves eventually connecting an antenna or a cable to the Raspberry Pi's GPIO 4 (pin 7).</p>
<img src="/assets/readme_assets/gpio.png"/>
<img src="/assets/readme_assets/example_gpio.jpg"/>

</details>

#### 2. Understanding the local client command line interface
The `local client` has a CLI to manage it. Write `help` for a list of all commands available.  

#### 3. Uploading files to the local client
The local client requires `wave` (`.wav`) files to play. To upload a file, you have two options:

**1. Upload a file stored on the local machine:** 
```sh
botwave> upload /home/server/Downloads/ss.wav ss.wav
```

**2. Upload a file stored on an external server:**
```sh
botwave> dl https://cdn.douxx.tech/files/ss.wav # download the file from cdn.douxx.tech
```

#### 4. Starting a broadcast
```sh
botwave> start ss.wav 88 # This starts broadcasting ss.wav on 88MHz
```

#### 5. Stopping a broadcast
```sh
botwave> stop
```

#### 6. Exiting properly
```sh
botwave> exit # this cleans up and exits
```


## Remote Management
BotWave allows you to manage remotely your `server` or `local client`. To do so, we recommend using a tool like [`BWSC`](https://github.com/douxxtech/bwsc).

#### 1. Install BWSC
```sh
npm i -g bwsc # this assumes you have npm and nodejs installed
```

#### 1. Setup the server or the local client
To allow you to connect remotely, you have to add the `--ws [PORT]` flag on the start command of the `server` or the `local client`. It is also recommended to add the `--pk [passkey]` flag to reject unauthorized connections.

```sh
bw-server --ws 9939 --pk 1234 # for the server component

bw-local --ws 9939 --pk 1234 # for the local client component
```

> note: if you add a passkey, you'll also have to provide it to the client: `sudo bw-client <server ip> --pk <passkey>`.

#### 2. Connect to the server/local client remotely
```sh
bwsc 192.168.1.10 1234 # assuming the server to be 192.168.1.10
```

#### 3. Manage the server/local client remotely
You will now have access to the `server`/`local client` CLI.  
Please note that the `<` and `exit` commands won't be available.  
You will also receive the server logs in real time.

```sh
botwave> help # server / lc will send the help back to you
```

## Advanced Usage
For other / more detailed actions please check the following resources:
- **Server help**: [`/server/server.md`](/server/server.md)
- **Client help**: [`/client/client.md`](/client/client.md)
- **Client help**: [`/local/local.md`](/local/local.md)
- **AutoRun help**: [`/autorun/autorun.md`](/autorun/autorun.md)
- **Automated actions help**: [`/misc_doc/handlers.md`](/misc_doc/handlers.md)
- **Remote management protocol**: [`/misc_doc/websocket.md`](/misc_doc/websocket.md)

### Updating BotWave
For debian-like systems, we recommend using our automatic uninstallation scripts, for other operating systems, you're on your own.

```bash
sudo bw-update
```

### Uninstallation
For debian-like systems, we recommend using our automatic uninstallation scripts, for other operating systems, you're on your own.

```bash
curl -sSL https://botwave.dpip.lol/uninstall | sudo bash
```

### BotWave Server For Cloud Instances
You can directly try BotWave `server` on Cloud Instances like Google Shell or GitHub Codespaces.  
[![Run in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/open?cloudshell_git_repo=https://github.com/dpipstudio/botwave&cloudshell_tutorial=misc_doc/google-shell.md&show=terminal)  
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dpipstudio/botwave)


## Mentions
**BotWave mentions**: Here are some posts that talk about BotWave. Thanks to their creators !
<div align="center"> <!-- centering a div ?? -->
<p></p>
<a href="https://news.ycombinator.com/item?id=46305516" target="_blank"><img src="assets/readme_assets/badge_show_hn.svg" alt="show hn"/></a>
<a href="https://korben.info/botwave-raspberry-pi-emetteur-fm-radio.html" target="_blank"><img src="assets/readme_assets/badge_le_site_de_korben.svg" alt="le site de korben"/></a>
<a href="https://www.cyberplanete.net/raspberry-pi-radio-botwave/" target="_blank"><img src="assets/readme_assets/badge_cyberplanete.svg" alt="cyberplanete"/></a>
</div>

## License
BotWave is licensed under [GPLv3.0](LICENSE).

## Credits

![a DPIP Studio Project](https://madeby.dpip.lol)
![Made by Douxx](https://madeby.douxx.tech)