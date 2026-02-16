# Handlers documentation

## Overview
Handlers are scripts that execute specific commands based on certain events. They are stored in a designated directory (default: `/opt/BotWave/handlers`, can be specified by using the --handlers-dir option) and must follow specific naming conventions and formatting rules.

## File Naming Conventions
Handler files must start with specific prefixes and have the correct file extensions:

- **Prefixes**:
  - `l_onready`: Executes when the system is ready. | `Local client`
  - `l_onstart`: Executes when the system starts. | `Local client`
  - `l_onstop`: Executes when the system stops. | `Local client`
  - `s_onready`: Executes when the system is ready. | `Server`
  - `s_onstart`: Executes when the system starts. | `Server`
  - `s_onstop`: Executes when the system stops. | `Server`
  - `s_onconnect`: Executes when a connection is established. | `Server`
  - `s_ondisconnect`: Executes when a connection is terminated. | `Server`
  - `s_onwsjoin`: Executes when a websocket connection is established. | `Server`
  - `s_onwsleave`: Executes when a websocket connection is terminated. | `Server`

- **Extensions**:
  - `.hdl`: Standard handler files.
  - `.shdl`: Silent handler files (no log messages for command execution).

## Handlers editor
BotWaves comes shipped with our own file validator and checker, named `bw-nanld`. Run it with `sudo bw-nanld <filename>` to automatically create the handler and validate input once you finished editing it. 

### bw-nandl
NanDl supports multiple operations:  
- Creating new handlers: `sudo bw-nandl <handler name | full path>` (eg `sudo bw-nandl s_onready.hdl`)
- Listing handlers: `sudo bw-nandl list`
- Showing handlers content: `sudo bw-nandl show <handler name | full path>` (eg `sudo bw-nandl show s_onready.hdl`)
- Editing an existing handler: `sudo bw-nandl open <handler name | full path>` (eg `sudo bw-nandl open s_onready.hdl`)

> [!TIP]
> NanDl defaults to `/opt/BotWave/handlers/` if a full path is not provided. Be sure of having that directory accessible. 

## File Formatting
Each line in a handler file represents a command to be executed. Ensure that:

- Each command is on a new line.
- Commands are clear and concise.
- Empty lines are ignored.

## Environment Variables
When a handler is executed, BotWave injects context as environment variables. These are available to any shell command or script called from within the handler.

### Always available
| Variable | Description |
|---|---|
| `BW_CLIENT_HOSTNAME` | Hostname of the machine running BotWave |
| `BW_CLIENT_MACHINE` | Machine architecture |
| `BW_CLIENT_SYSTEM` | OS name |
| `BW_CLIENT_PROTO` | Protocol version |
| `BW_UPLOAD_DIR` | Upload directory path |
| `BW_HANDLERS_DIR` | Handlers directory path |
| `BW_WS_PORT` | WebSocket port (`0` if unset) |
| `BW_PASSKEY_SET` | `true` or `false` |

### Event-specific variables

| Event | Extra variables |
|---|---|
| `l_onstart` / `s_onstart` | `BW_BROADCAST_FILE`, `BW_BROADCAST_FREQ` |
| `l_onstop` / `s_onstop` | `BW_BROADCAST_FILE` |
| `s_onconnect` / `s_ondisconnect` | `BW_CLIENT_ID`, `BW_CLIENT_HOSTNAME`, `BW_CLIENT_MACHINE`, `BW_CLIENT_SYSTEM`, `BW_CLIENT_PROTO`, `BW_CLIENT_CONNECTED_AT` |

### Example usage
You can access these in a shell script called from a handler:
```plaintext
< echo $BW_BROADCAST_FILE
< notify-send "Now broadcasting $BW_BROADCAST_FILE on $BW_BROADCAST_FREQ MHz"
```
```plaintext
# whitelist system (s_onconnect.hdl)
| [[ ! "pi1 pi2 radpi" =~ $BW_CLIENT_HOSTNAME ]] && echo "< kick $BW_CLIENT_HOSTNAME \"whitelist enabled\""
```

## Example Handler File
Here is an example of a properly formatted handler file named `s_onready.hdl`:

```plaintext
command1
command2
command3
```

## Silent Handler Example
Here is an example of a silent handler file named `s_onready.shdl`:

```plaintext
silent_command1
silent_command2
silent_command3
```

## Directory Structure
Ensure that all handler files are placed in the correct directory as specified by the system configuration. The default directory is typically named `handlers_dir`.

## Logging
- Standard handler files (`.hdl`) will log messages indicating which commands are being executed.
- Silent handler files (`.shdl`) will not log these messages.

## Error Handling
Errors during the execution of handler files will be logged. Ensure that commands in handler files are tested and validated to minimize errors.