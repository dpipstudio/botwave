<div align=center>

<img src="https://images.dpip.lol/bw-logo-big.png" alt="BotWave"/>

<h1> BotWave - Your RPI FM Network </h1>
<h4> <a href="https://botwave.dpip.lol">Website</a></h4>   
</div>

> [!WARNING]
> The latest release of BotWave introduces a brand new protocol, and may not work as desired. Please open an issue if encountering any issue.

BotWave is a system for broadcasting audio files over FM radio using Raspberry Pi devices. It consists of a server and client application that work together to manage and broadcast audio files.  
It uses [bw_custom](https://github.com/dpipstudio/bw_custom) as a backend, based on [PiFmRds](https://github.com/ChristopheJacquet/PiFmRds).

## Features

- **Server-Client Architecture**: Manage multiple Raspberry Pi clients from a central server.
- **Audio Broadcasting**: Broadcast audio files over FM radio.
- **File Upload**: Upload audio files to clients for broadcasting.
- **Remote Management**: Start, stop, and manage broadcasts remotely.
- **Authentication**: Client-server authentication with passkeys.
- **Protocol Versioning**: Ensure compatibility between server and clients.

## Requirements 
> All requirements can be auto-installed with the automatic installer, see below.

### Server
- Python >= 3.6

### Client
- Raspberry Pi
- Root access
- Python >= 3.6
- [bw_custom](https://github.com/dpipstudio/bw_custom)
- (Wire or antenna)

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Safety Note**: To minimize interference and stay within your intended frequency range, it is strongly recommended to use a band-pass filter when operating BotWave.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions, equipment, and knowledge of regulations before using BotWave for broadcasting purposes.


> [!NOTE]
> We have a W.I.P wiki that explains some basics about BotWave. We recommand reading it at least once: [`/wiki`](https://github.com/dpipstudio/botwave/wiki)

For debian-like systems, we recommand using our automatic installation scripts, for other operating systems, you're on your own.

```bash
curl -sSL https://botwave.dpip.lol/install | sudo bash
```
<details>
<summary><code>Installer options</code></summary>
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

### BotWave Server For Cloud Instances
You can directly try BotWave `server` on Cloud Instances like Google Shell or GitHub Codespaces !  
[![Run in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://shell.cloud.google.com/cloudshell/open?cloudshell_git_repo=https://github.com/dpipstudio/botwave&cloudshell_tutorial=misc_doc/google-shell.md&show=terminal)  
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/dpipstudio/botwave)

## Hardware installation
To use BotWave Client for broadcasting, you need to set up the hardware correctly. This involves connecting an antenna or a cable to the Raspberry Pi's GPIO 4 (pin 7).

<div align="center"> <img src="assets/readme_assets/gpio.png" alt="BotWave" width="300"/></div>


## Updating BotWave
For debian-like systems, we recommand using our automatic uninstallation scripts, for other operating systems, you're on your own.

```bash
sudo bw-update
```

## Uninstallation
For debian-like systems, we recommand using our automatic uninstallation scripts, for other operating systems, you're on your own.

```bash
curl -sSL https://botwave.dpip.lol/uninstall | sudo bash
```

## Usage

BotWave usage depends on the tool you're using. Here's a breakdown of each component:

### **Server**
> This tool is included in the **SERVER** install.
The BotWave Server lets you manage multiple Raspberry Pi clients remotely, upload audio files, control broadcasts, and more.

**Full documentation:** [server/server.md](server/server.md)

---

### **Client**
> This tool is included in the **CLIENT** install.
The BotWave Client runs on a Raspberry Pi and connects to the server to receive and broadcast audio files over FM.

**Full documentation:** [client/client.md](client/client.md)

---

### **Local Client**
> This tool is included in the **CLIENT** install.
The Local Client allows you to broadcast audio files **without a server**, directly from the Raspberry Pi using command-line controls.

**Full documentation:** [local/local.md](local/local.md)

---

### **AutoRunner**
> This tool is included in the **CLIENT & SERVER** install.
The AutoRunner lets you set up `systemd` services to automatically start the BotWave Client or Server on boot.

**Full documentation:** [autorun/autorun.md](autorun/autorun.md)

---

*We highly recommend using the automatic installer to set up the desired components (`server`, `client`, or `both`):*

```bash
curl -sSL https://botwave.dpip.lol/install | sudo bash -s <server, client or both>
```

## ETC
**They talk about BotWave**: Here are some posts that talk about BotWave. Thanks to their creators !
<details>
<summary><code>They talk about us</code></summary>
<p></p>
<div align="center"> <!-- centering a div ?? -->
<a href="https://korben.info/botwave-raspberry-pi-emetteur-fm-radio.html" target="_blank"><img src="assets/readme_assets/badge_le_site_de_korben.svg" alt="le site de korben"/></a>
<a href="https://www.cyberplanete.net/raspberry-pi-radio-botwave/" target="_blank"><img src="assets/readme_assets/badge_cyberplanete.svg" alt="cyberplanete"/></a>
</div>
</details>

## License
BotWave is licensed under [GPLv3.0](LICENSE).

## Credits

![a DPIP Studio Project](https://madeby.dpip.lol)
![Made by Douxx](https://madeby.douxx.tech)
