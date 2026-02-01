# BotWave - AutoRunner | Documentation

> This tool is included in the **CLIENT & SERVER** install.

BotWave AutoRunner is a server / client application allowing you to manage easily systemd services, allowing you to create autorun scripts for BotWave Client and BotWave Server, starting immediatly when booting up your device.

## Requirements
* Root Access
* Python 3.6

## Installation

> [!WARNING]
> **Warning**: Using BotWave involves broadcasting signals which may be subject to local regulations and laws. It is your responsibility to ensure that your use of BotWave complies with all applicable legal requirements and regulations in your area. Unauthorized use of broadcasting equipment may result in legal consequences, including fines or penalties.
>
> **Safety Note**: To minimize interference and stay within your intended frequency range, it is strongly recommended to use a band-pass filter when operating BotWave.
>
> **Liability**: The author of BotWave is not responsible for any damage, loss, or legal issues that may arise from the use of this software. By using BotWave, you agree to accept all risks and liabilities associated with its operation and broadcasting capabilities.
>
> Please exercise caution and ensure you have the proper permissions, equipment, and knowledge of regulations before using BotWave for broadcasting purposes.


We highly recommand using the official installer (Check the [main README](/README.md)) -- If you don't want to or are not using a Linux distribution, find how to install it by yourself. (Tip: on windows, use wsl)

## Usage
To start the BotWave AutoRunner, use the following command:

```bash
sudo bw-autorun <client, server, local> [additional arguments to add to command line]
```

### Arguments
* `--start`: Starts the client / server if not already started.
* `--stop`: Stops the client / server if not already stopped.
* `--status`: Shows logs of the client / server.
* `--uninstall`: Uninstalls the client / server autorun.

### Example
```bash
# install the autorunner for client
sudo bw-autorun client 192.168.1.100 --pk mypasskey

# install the autorunner for server
sudo bw-autorun server --pk mypasskey

# install the autorunner for local
sudo bw-autorun local

# view logs
sudo bw-autorun --status client

# uninstall client
sudo bw-autorun --uninstall client
```