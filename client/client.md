# BotWave - Client | Documentation

> This tool is included in the **CLIENT** install.

BotWave Client is a client application designed to connect to a BotWave Server, allowing for the upload and broadcast of audio files over FM radio using a Raspberry Pi.

## Requirements
* Raspberry Pi - Officially working : RPI 0 1, 2, 3, and 4
* Root Access
* Python >= 3.6
* [bw_custom](https://github.com/dpipstudio/bw_custom) installed
* [PiWave](https://github.com/douxxtech/piwave) python module

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Safety Note**: To minimize interference and stay within your intended frequency range, it is strongly recommended to use a band-pass filter when operating BotWave.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions, equipment, and knowledge of regulations before using BotWave for broadcasting purposes.

We highly recommand using the official installer (Check the [main README](/README.md)) -- Note that if you aren't on a raspberry pi, the client is very unlikely to work.

## Usage
To start the BotWave Client, use the following command:

```bash
sudo bw-client [server_host] [--port PORT] [--upload-dir UPLOAD_DIR] [--skip-checks] [--pk PASSKEY] [--skip-update-check]
```

### Arguments
* `server_host`: The hostname or IP address of the BotWave Server. Will prompt for value if not provided.
* `--port`: The port on which the server is listening (default: `9938`).
* `--fport`: The port on which the server is listening (default: `9921`).
* `--upload-dir`: The directory to store uploaded files (default: `/opt/BotWave/uploads`).
* `--skip-checks`: Skip system requirements checks.
* `--pk`: Optional passkey for authentication.
* `--skip-update-check`: Skip checking for protocol updates.

### Example
```bash
sudo bw-client 9.9.9.9 --port 9939 --upload-dir /tmp/my_uploads --pk mypasskey
```

---

![a DPIP Studio Project](https://madeby.dpip.lol)
![Made by Douxx](https://madeby.douxx.tech)
