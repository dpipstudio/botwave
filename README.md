<div align=center>

<img src="assets/botwave_icon.png" alt="BotWave" width="300"/>

<h1> BotWave - Your RPI FM Network </h1>
<h4> <a href="https://botwave.dpip.lol">botwave.dpip.lol btw</a></h4>   
</div>

BotWave is a system for broadcasting audio files over FM radio using Raspberry Pi devices. It consists of a server and client application that work together to manage and broadcast audio files.

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
- Python 3.x

### Client
- Raspberry Pi (recommended)
- Root access
- PiFmRds installed
- Python 3.x
- PiWave module

## Installation

For *nix systems, we recommand using our automatic installation scripts, for other operating systems, you're on your own.

```bash
curl -sSL https://botwave.dpip.lol/install | sudo bash -s <server, client or both>
```

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Safety Note**: To minimize interference and stay within your intended frequency range, it is strongly recommended to use a band-pass filter when operating BotWave.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions, equipment, and knowledge of regulations before using BotWave for broadcasting purposes.

## Hardware installation
To use BotWave Client for broadcasting, you need to set up the hardware correctly. This involves connecting an antenna or a cable to the Raspberry Pi's GPIO 4 (pin 7).

<div align="center"> <img src="assets/gpio.png" alt="BotWave" width="300"/></div>


## Updating BotWave
For *nix systems, we recommand using our automatic uninstallation scripts, for other operating systems, you're on your own.

```bash
sudo bw-update
```

## Uninstallation
For *nix systems, we recommand using our automatic uninstallation scripts, for other operating systems, you're on your own.

```bash
curl -sSL https://botwave.dpip.lol/uninstall | sudo bash
```

## Usage

BotWave usage depends on the tool you're using. Here's a breakdown of each component:

### **Server**
> This tool is included in the **SERVER** install.
The BotWave Server lets you manage multiple Raspberry Pi clients remotely — upload audio files, control broadcasts, and more.

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

## License
BotWave is licensed under [GPLv3.0](LICENSE).

## Credits

![a DPIP Studio Project](https://madeby.dpip.lol)
![Made by Douxx](https://madeby.douxx.tech)
