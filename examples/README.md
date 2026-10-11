# BotWave Examples

This directory contains automation examples for BotWave.  
Its structure is based on the [dpipstudio/bw_plugin](https://github.com/dpipstudio/bw_plugin) repository.

Find more help about automation in [`Main/Automate your setup`](https://github.com/dpipstudio/botwave/wiki/Automate-your-setup), [`Advanced/Creating custom commands`](https://github.com/dpipstudio/botwave/wiki/Creating-custom-commands), and [`For Developers/Creating a plugin`](https://github.com/dpipstudio/botwave/wiki/Creating-a-plugin).

## What it ships
Currently, this directory contains:
- The `update-botwave` command, that runs `bw-update` then restarts the `bw-server` or `bw-local` systemd service.
- The `set-prompt` command, that updates the command prompt.
- A welcome banner on server and local client startup.
- A welcome banner for remote clients joins and leaves.
- A "Last login on" SSH-like log on remote client joins.

## Installation

```bash
sudo bash install.sh
```

Copies scripts to `/opt/BotWave/scripts/bw_examples/` and handlers to `/opt/BotWave/handlers/`.

## Removal

```bash
sudo bash uninstall.sh
```