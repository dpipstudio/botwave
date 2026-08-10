A BotWave plugin is a self-contained extension that adds behavior to a running BotWave instance — new commands, automated reactions to events, or both. Plugins don't modify BotWave itself; they sit alongside it, using the same handler and custom command system that's already built in.

> [!NOTE]
> This page is aimed at developers. Before reading this, make sure you're comfortable with [Advanced/Creating custom commands](https://github.com/dpipstudio/botwave/wiki/Creating-custom-commands) and [Main/Automate your setup](https://github.com/dpipstudio/botwave/wiki/Automate-your-setup).

## What a plugin actually is

There's no special plugin API, no registration step, no manifest file. A plugin is just a collection of:

- **`.cmd` files** in `/opt/BotWave/handlers/`: custom commands your plugin exposes
- **`.hdl` / `.shdl` files** in `/opt/BotWave/handlers/`: event handlers that react to BotWave lifecycle events
- **Shell scripts** in `/opt/BotWave/scripts/<yourplugin>/`: the actual logic, called from the above

An `install.sh` copies everything into place. An `uninstall.sh` removes it. That's the full surface area.

BotWave picks up `.cmd` files on every command run (hot-reload), and loads `.hdl`/`.shdl` files at startup and on relevant events. Your plugin is active as soon as its files are in the right directories.

## Template repo

The fastest way to get started is [`dpipstudio/bw_plugin`](https://github.com/dpipstudio/bw_plugin). It's a GitHub template repo with a working example, a correct directory structure, and install/uninstall scripts ready to go.

```bash
# Use the template on GitHub (recommended), or clone it directly:
git clone https://github.com/dpipstudio/bw_plugin.git bw_myplugin
cd bw_myplugin
```

Then:
1. Replace every occurrence of `myplugin` with your plugin's name
2. Edit or replace the example files
3. Update the README

## Building from scratch
If you'd rather not use the template, here's what the structure looks like:

```
bw_myplugin/
├── handlers/
│   ├── mycommand.cmd            # custom command
│   ├── s_onready_myplugin.shdl  # startup handler (silent)
│   └── s_onexit_myplugin.shdl   # exit handler (silent)
├── scripts/
│   └── mycommand.sh             # logic for mycommand.cmd
├── install.sh
└── uninstall.sh
```

### The command

`handlers/mycommand.cmd`:
```
#!/*/mycommand
# mycommand <arg1> [arg2]
#   Does something useful.

< bash /opt/BotWave/scripts/myplugin/mycommand.sh
```

`scripts/mycommand.sh`:
```bash
#!/bin/bash

if [[ -z "$BW_ARGV1" ]]; then
    echo "Usage: mycommand <arg1> [arg2]"
    exit 0
fi

echo "arg1: $BW_ARGV1"
[[ -n "$BW_ARGV2" ]] && echo "arg2: $BW_ARGV2"
```

Arguments are available as `BW_ARGV{n}` environment variables, 0-indexed, with `BW_ARGV0` always being the command name itself. So user-supplied args start at `BW_ARGV1`.

### The handlers

`handlers/s_onready_myplugin.shdl`:
```plaintext
# Runs silently when BotWave is ready.
< echo "[myplugin] loaded."
```

`handlers/s_onexit_myplugin.shdl`:
```plaintext
# Runs silently when BotWave exits.
< echo "[myplugin] unloaded."
```

Use `.shdl` for handlers that don't need to log every command they run.

For the full list of available event prefixes (`s_onconnect`, `s_onstart`, etc.) and the environment variables injected at each event, see [Main/Automate your setup](https://github.com/dpipstudio/botwave/wiki/Automate-your-setup).

### install.sh

```bash
#!/bin/bash

PLUGIN_NAME="myplugin"
BW_INSTALL="/opt/BotWave"

if [ "$EUID" -ne 0 ]; then
    echo "Error: run as root (sudo bash install.sh)"
    exit 1
fi

if [ ! -d "$BW_INSTALL" ]; then
    echo "Error: BotWave not found at $BW_INSTALL"
    exit 1
fi

mkdir -p "$BW_INSTALL/scripts/$PLUGIN_NAME"
cp scripts/* "$BW_INSTALL/scripts/$PLUGIN_NAME/"
chmod +x "$BW_INSTALL/scripts/$PLUGIN_NAME/"*.sh

cp handlers/* "$BW_INSTALL/handlers/"

echo "$PLUGIN_NAME installed."
```

### uninstall.sh

```bash
#!/bin/bash

PLUGIN_NAME="myplugin"
BW_INSTALL="/opt/BotWave"

if [ "$EUID" -ne 0 ]; then
    echo "Error: run as root (sudo bash uninstall.sh)"
    exit 1
fi

rm -rf "$BW_INSTALL/scripts/$PLUGIN_NAME"

for f in handlers/*; do
    rm -f "$BW_INSTALL/handlers/$(basename $f)"
done

echo "$PLUGIN_NAME uninstalled."
```

The uninstall loop only removes the files your plugin installed, it won't touch anything else in the handlers directory.

## Naming your handlers

Since all plugins drop files into the same `/opt/BotWave/handlers/` directory, prefixing your handler filenames with your plugin name avoids collisions with other plugins or the user's own handlers:

```
s_onready_myplugin.shdl    ✓
s_onready.shdl             ✗  (too generic, likely to conflict)
```

For multiple handlers on the same event, use numbered names to control execution order:

```
s_onready_myplugin_01_init.shdl
s_onready_myplugin_02_start.shdl
```

Handlers on the same prefix run in alphabetical order.

## Real-world examples

- [`bw_wtt`](https://github.com/douxxtech/bw_wtt) — WebSocket to TCP bridge. Good example of a plugin that combines handlers and scripts to integrate an external service.
- [`cloud-install`](https://github.com/dpipstudio/botwave/blob/main/misc/cloud-install.sh) — Our own integrated plugin to automatically start a port forwarding on cloud instances of BotWave server.