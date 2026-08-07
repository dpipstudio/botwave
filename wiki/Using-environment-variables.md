Environment variables let you configure BotWave flexibly without modifying source files. They can be set in a `.env` file, as real shell environment variables, or changed at runtime via the CLI.

> **Priority order:** CLI arguments > `.env` file (or shell environment) > built-in defaults.
> **Immutability:** Some variables are locked after startup. See [Variable Immutability](#variable-immutability).

> [!NOTE]
> You can find the full list of the currently supported variables [at the bottom of this page](#environment-variables).

# In-app usage
Environment variables can be changed directly via the BotWave CLI, and do not need any reload after setting them. Please note that **the environment variables being set this way are ephemeral**, and won't persist after exiting the program.

> Note: **Environment variables usage in BotWave is case-insensitive**.
> This means that `MyVar` will be the same as `mYvAr`.

## Getting a Variable
Once in a BotWave shell, you can get the value of a environment variable using the `get` command. Here are some examples:

```bash
botwave › get port # get single env var
[ENV] (PORT) 9938

botwave › get host port fport # get multiple env vars
[ENV] (HOST) 0.0.0.0
[ENV] (PORT) 9938
[ENV] (FPORT) 9921

botwave › get * # get every env var
[ENV] (SHELL) /bin/bash
[ENV] (SUDO_GID) 1000
[...]
```

## Setting a Variable
The `set` command lets you set the value of a environment variable. The variable is created if non-existent.

```bash
botwave › set prompt_text "BwServer $ " # setting / changing env var value
[ENV] (PROMPT_TEXT) BwServer $

BwServer $ # the prompt changed !
```

## Variable interpolation
Commands support `{VAR}` syntax to inject environment variables directly into BotWave commands:

```bash
botwave › < echo This is the current prompt: "{prompt_text}"
This is the current prompt: botwave ›
```

# Variable Immutability
Some BotWave environment variables are designed to **not** be modified. Those are called **immutable variables**. Editing those **at runtime** may result in unexpected results, and isn't recommended.

> Immutable variable content will be logged in orange when retrieved.

Trying to change them using the built-in setter will result in an error:

```bash
botwave › set host 127.0.0.1
[ENV] Provided key (host) is immutable. Changes are not recommended, but can be done by replacing it with another immutable string. Consider yourself warned.
```

However, as said in the message, you can modify by replacing it by another immutable one. This can be done with the setter:

```bash
botwave › set host "127.0.0.1" true # format: set <key> <value> [immutable]
[ENV] (HOST) 127.0.0.1
```

You can also set an initially mutable variable to an immutable one using the same command.

```bash
botwave › set prompt_text "BwServer $ " true
[ENV] (PROMPT_TEXT) BwServer $

BwServer $ set prompt_text "botwave › "
[ENV] Provided key (prompt_text) is immutable. Changes are not recommended, but can be done by replacing it with another immutable string. Consider yourself warned.
```

# In-shell usage
Environment variables can also be set before running BotWave, directly in the shell.
For example, let's run the server as a daemon using bash:

```bash
DAEMON=true sudo -E bw-server # the -E flag is required to use the current environment as sudo!
BotWave - Server

[INFO] Running in daemon mode. Server will continue to run in the background.
[TLS] Generated self-signed TLS certificate
[...]
```

You can set immutable variables by wrapping them into `immutable(<var>)`:

```bash
myvar='immutable(hi)' sudo -E bw-server # the -E flag is required to use the current environment as sudo!
BotWave - Server

[TLS] Generated self-signed TLS certificate
[...]

botwave › set myvar bye
[ENV] Provided key (myvar) is immutable. Changes are not recommended, but can be done by replacing it with another immutable string. Consider yourself warned.
```

# DotEnv
BotWave supports loading environment variables from a `.env` file, with a `key=value` format.

```bash
DEFAULT_PI="MyRad"
DEFAULT_RT="The best radio to ever exist !"
WS_CMD_PORT=9939

# this is dangerous, gaining ws remote shell access -> gaining system access
# (unblocks '<', '|', 'get', 'set', [...] commands)
ALLOW_WS_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING=true

upload_dir="immutable(/home/server/bw_upl/)"
prompt_text="immutable(BwServer $ )"
```

BotWave will, by default, use the `.env` file in the current directory to load variables.
A custom path can be used by setting `DOTENV_PATH` in the shell session or by using the `--config` flag:

```bash
DOTENV_PATH="/opt/BotWave/.env" sudo -E bw-server
# or
sudo bw-server --config /opt/BotWave/.env
```

> [!WARNING]
> BotWave will silently ignore a malformed `.env` line (e.g. missing `=`, stray quotes). If a variable isn't loading as expected, double-check the syntax of that line.

# Environment Variables

Here is a full list of every supported variable, organized by component.

## Server (`bw-server`)

| Variable | Type | Default | Immutable | Notes |
|---|---|---|---|---|
| **General** | | | | |
| `HOST` | str | `0.0.0.0` | yes | Address the WebSocket server binds to. |
| `PORT` | int | `9938` | yes | Main WebSocket server port. |
| `FPORT` | int | `9921` | yes | HTTP file transfer server port. |
| `PASSKEY` | str | *(none)* | yes | Authentication passkey for incoming connections. If unset, no auth is required. |
| `WAIT_START` | bool | `true` | no | Tries to synchronize broadcasts. Set to `false` via `--start-asap`. |
| `DAEMON` | bool | `false` | yes | Run the process in daemon mode. |
| `SKIP_CHECKS` | bool | `false` | no | Skip the different startup checks. |
| `EXTRA_ALLOWED_DIRS` | str | The process PWD | no | `:`-separated extra directories allowed for file reads. |
| `HANDLERS_DIR` | str | `/opt/BotWave/handlers/` | no | Directory where `.hdl` and `.shdl` handler files are loaded from. |
| `ALLOW_PROTO_MISMATCH` | bool | `false` | no | Skip strict protocol version matching between client and server. |
| `DEFAULT_FREQ` | int | `90` | no | Default FM broadcast frequency in MHz. |
| `DEFAULT_PI` | str | `FFFF` | no | Default RDS Programme Identifier code. |
| `DEFAULT_PS` | str | `BotWave` | no | Default RDS Programme Service name (max 8 characters). |
| `DEFAULT_RT` | str | `Broadcasting` | no | Default RDS RadioText string. |
| `DEFAULT_MORSE_WPM` | int | `20` | no | Default Morse code speed in words per minute. |
| `MORSE_FREQUENCY` | int | `700` | no | Tone frequency for Morse audio output in Hz. |
| `MORSE_SAMPLE_RATE` | int | `48000` | no | Sample rate for Morse WAV output in Hz. |
| `CMD_INTERPRETER` | str | *(none)* | no | The command interpreter to use for shell and pipe commands (`<`, `\|`) |
| `PROMPT_TEXT` | str | `botwave › ` | no | Text displayed as the CLI prompt. |
| `HISTORY_PATH` | str | `/opt/BotWave/.history` | no | Path to the CLI command history file. |
| `DOTENV_PATH` | str | `.env` | no | Path to the `.env` file. Must be set before launch to take effect. |
| **HTTP File Server** | | | | |
| `UPLOAD_DIR` | str | `/opt/BotWave/uploads/` | no | Directory served by the HTTP file server. |
| `FTOKEN_LIFETIME` | int | `300` | no | File access token lifetime in seconds. |
| `HTTP_MAX_UPLOAD_SIZE` | int | `1073741824` | no | Maximum upload size in bytes (default 1 GB). |
| `HTTP_CHUNK_SIZE` | int | `65536` | no | Chunk size in bytes for file transfers. |
| **Remote Command Handler** | | | | |
| `REMOTE_CMD_PORT` | int | *(none)* | yes | Port the remote command handler listens on. Disabled if not set. *(formerly `WS_CMD_PORT`)* |
| `REMOTE_BLOCKED_CMD` | str | `get,set,<,\|` | no | Comma-separated list of commands blocked over remote connection. *(formerly `WS_BLOCKED_CMD`)* |
| `ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING` | bool | `false` | no | Bypasses the blocked command list. Grants full remote shell access. Use only in isolated/trusted environments. |
| `INTERPOLATE_REMOTE` | bool | `false` | no | Allow environment variables interpolation in remote commands. |
| `REMOTE_CMD_WELCOME` | str | *(none)* | no | Message displayed to clients upon connecting to the remote command handler. |
| `REMOTE_CMD_PWD_TIMEOUT` | int | `60` | no | Seconds before an unauthenticated connection is dropped. |
| `ISOLATE_REMOTE` | bool | `true` | no | If true, output from a remotely executed command is sent only to the client that triggered it. Still logged to stdout and log files regardless. |
| **TLS / Certificates** | | | | |
| `TLS_KEY_SIZE` | int | `2048` | no | RSA key size for the auto-generated self-signed certificate. |
| `CERT_COMMON` | str | `BotWave-Server` | no | Certificate Common Name (CN). |
| `CERT_ORG` | str | `DPIP Studio` | no | Certificate Organization Name. |
| `CERT_UNIT` | str | `BotWave` | no | Certificate Organizational Unit. |
| `CERT_SAN_DNS` | str | `localhost` | no | Subject Alternative Name / DNS entry. |
| `CERT_SAN_IP` | str | `127.0.0.1` | no | Subject Alternative Name / IP entry. |
| `CERT_VALIDITY_DAYS` | int | `365` | no | Certificate validity period in days. |
| **ALSA** | | | | |
| `ALSA_INTERFACE` | str | `hw` | no | ALSA interface for loopback capture. |
| `ALSA_CARD` | str | `BotWave` | no | ALSA soundcard name for loopback capture. |
| `ALSA_DEVICE` | str | `0` | no | ALSA device id for loopback capture. |
| `ALSA_RATE` | int | `48000` | no | ALSA capture sample rate in Hz. Also used when streaming live ALSA audio over HTTP. |
| `ALSA_CHANNELS` | int | `2` | no | Number of audio channels for ALSA capture. Also used when streaming live ALSA audio over HTTP. |
| `ALSA_PERIODSIZE` | int | `1024` | no | ALSA period size in frames. |
| **SSTV** | | | | |
| `SSTV_DEFAULT_MODE` | str | *(auto-selected)* | no | Default SSTV encoding mode (e.g. `Robot36`). Auto-selected from image dimensions if unset. |
| `SSTV_SAMPLE_RATE` | int | `48000` | no | Sample rate for SSTV WAV output in Hz. |
| **Converter** | | | | |
| `CONVERTER_SAMPLE_RATE` | str | `48000` | no | Output sample rate used when converting files to WAV via ffmpeg. |
| `CONVERTER_CHANNELS` | str | `2` | no | Number of output channels used when converting files to WAV. |
| **Logging** | | | | |
| `REDACT_IPV4` | bool | `false` | no | Replaces all IPv4 addresses in log output with `[REDACTED]`. |
| `LOG_FILE` | str | *(none)* | no | Path to a file where logs will be written. Disabled if not set. |
| `LOG_TIME` | bool | `false` | no | If `true`, a timestamp is prepended to each log entry. |
| `LOG_TIME_FORMAT` | str | `%Y-%m-%d %H:%M:%S` | no | Timestamp format used when `LOG_TIME` is enabled. |
| **User-Agents** | | | | |
| `VCHECK_UA` | str | `BotWaveVCheck/<version> (+https://github.com/dpipstudio/botwave/)` | no | User-Agent string for version check requests. |

## Local Client (`bw-local`)

| Variable | Type | Default | Immutable | Notes |
|---|---|---|---|---|
| **General** | | | | |
| `HOST` | str | `0.0.0.0` | yes | Bound host address (used when running locally with remote command handler). |
| `PASSKEY` | str | *(none)* | yes | Passkey for the local remote command handler. |
| `DAEMON` | bool | `false` | yes | Run the process in daemon mode. |
| `SKIP_CHECKS` | bool | `false` | no | Skip Raspberry Pi detection and other checks on startup. |
| `TALK` | bool | `false` | no | Enable verbose/debug output. |
| `UPLOAD_DIR` | str | `/opt/BotWave/uploads/` | no | Directory for local file operations. |
| `HANDLERS_DIR` | str | `/opt/BotWave/handlers/` | no | Directory where `.hdl` and `.shdl` handler files are loaded from. |
| `DEFAULT_FREQ` | int | `90` | no | Default FM broadcast frequency in MHz. |
| `DEFAULT_PI` | str | `FFFF` | no | Default RDS Programme Identifier code. |
| `DEFAULT_PS` | str | `BotWave` | no | Default RDS Programme Service name (max 8 characters). |
| `DEFAULT_RT` | str | `Broadcasting` | no | Default RDS RadioText string. |
| `DEFAULT_MORSE_WPM` | int | `20` | no | Default Morse code speed in words per minute. |
| `MORSE_FREQUENCY` | int | `700` | no | Tone frequency for Morse audio output in Hz. |
| `MORSE_SAMPLE_RATE` | int | `48000` | no | Sample rate for Morse WAV output in Hz. |
| `CMD_INTERPRETER` | str | *(none)* | no | The command interpreter to use for shell and pipe commands (`<`, `\|`) |
| `PROMPT_TEXT` | str | `botwave › ` | no | Text displayed as the CLI prompt. |
| `HISTORY_PATH` | str | `/opt/BotWave/.history` | no | Path to the CLI command history file. |
| `DOTENV_PATH` | str | `.env` | no | Path to the `.env` file. Must be set before launch to take effect. |
| **Remote Command Handler** | | | | |
| `REMOTE_CMD_PORT` | int | *(none)* | yes | Port the remote command handler listens on. Disabled if not set. *(formerly `WS_CMD_PORT`)* |
| `REMOTE_BLOCKED_CMD` | str | `get,set,<,\|` | no | Comma-separated list of commands blocked over remote connection. *(formerly `WS_BLOCKED_CMD`)* |
| `ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING` | bool | `false` | no | Bypasses the blocked command list. Grants full remote shell access. Use only in isolated/trusted environments. |
| `INTERPOLATE_REMOTE` | bool | `false` | no | Allow environment variables interpolation in remote commands. |
| `REMOTE_CMD_WELCOME` | str | *(none)* | no | Message displayed to clients upon connecting to the remote command handler. |
| `REMOTE_CMD_PWD_TIMEOUT` | int | `60` | no | Seconds before an unauthenticated connection is dropped. |
| `ISOLATE_REMOTE` | bool | `true` | no | If true, output from a remotely executed command is sent only to the client that triggered it. Still logged to stdout and log files regardless. |
| **ALSA** | | | | |
| `ALSA_INTERFACE` | str | `hw` | no | ALSA interface for loopback capture. |
| `ALSA_CARD` | str | `BotWave` | no | ALSA soundcard name for loopback capture. |
| `ALSA_DEVICE` | str | `0` | no | ALSA device id for loopback capture. |
| `ALSA_RATE` | int | `48000` | no | ALSA capture sample rate in Hz. |
| `ALSA_CHANNELS` | int | `2` | no | Number of audio channels for ALSA capture. |
| `ALSA_PERIODSIZE` | int | `1024` | no | ALSA period size in frames. |
| **SSTV** | | | | |
| `SSTV_DEFAULT_MODE` | str | *(auto-selected)* | no | Default SSTV encoding mode (e.g. `Robot36`). Auto-selected from image dimensions if unset. |
| `SSTV_SAMPLE_RATE` | int | `48000` | no | Sample rate for SSTV WAV output in Hz. |
| **Converter** | | | | |
| `CONVERTER_SAMPLE_RATE` | str | `48000` | no | Output sample rate used when converting files to WAV via ffmpeg. |
| `CONVERTER_CHANNELS` | str | `2` | no | Number of output channels used when converting files to WAV. |
| **Backend** | | | | |
| `BACKEND_PATH` | str | *(auto-discovered)* | no | Full path to the backend executable. Searched automatically if unset. |
| `BACKEND_MIN_FREQ` | int | `76` | no | The minimum frequency the backend is able to operate on, in MHz. |
| `BACKEND_MAX_FREQ` | int | `108` | no | The maximum frequency the backend is able to operate on, in MHz. |
| `BACKEND_BYPASS_CACHE` | bool | `false` | no | Set to true to refresh the cached backend path(s). |
| **Resource Monitor** | | | | |
| `RESOURCE_POLL_INTERVAL` | int | `10` | no | How often to check CPU and RAM usage, in seconds. Only active during a broadcast. |
| `RESOURCE_WARN_COOLDOWN` | int | `60` | no | Minimum time between repeated resource warnings, in seconds. |
| `RESOURCE_CPU_THRESHOLD` | int | `80` | no | CPU usage percentage that triggers a warning. |
| `RESOURCE_RAM_THRESHOLD` | int | `90` | no | RAM usage percentage that triggers a warning. |
| **Logging** | | | | |
| `REDACT_IPV4` | bool | `false` | no | Replaces all IPv4 addresses in log output with `[REDACTED]`. |
| `LOG_FILE` | str | *(none)* | no | Path to a file where logs will be written. Disabled if not set. |
| `LOG_TIME` | bool | `false` | no | If `true`, a timestamp is prepended to each log entry. |
| `LOG_TIME_FORMAT` | str | `%Y-%m-%d %H:%M:%S` | no | Timestamp format used when `LOG_TIME` is enabled. |
| **User-Agents** | | | | |
| `VCHECK_UA` | str | `BotWaveVCheck/<version> (+https://github.com/dpipstudio/botwave/)` | no | User-Agent string for version check requests. |
| `DOWNLOAD_UA` | str | `BotWaveDownloads/<version> (+https://github.com/dpipstudio/botwave/)` | no | User-Agent string for file download requests. |

## Client (`bw-client`)

| Variable | Type | Default | Immutable | Notes |
|---|---|---|---|---|
| **General** | | | | |
| `SERVER_HOST` | str | *(prompted)* | yes | Remote server hostname or IP. User is prompted at startup if not set. |
| `SERVER_PORT` | int | `9938` | yes | Remote server port. |
| `FHOST` | str | `SERVER_HOST` | yes | File server host for transfers. Defaults to `SERVER_HOST` if not set. |
| `FPORT` | int | `9921` | yes | Remote HTTP file transfer server port. |
| `PASSKEY` | str | *(none)* | yes | Passkey sent to the server during authentication. |
| `SKIP_CHECKS` | bool | `false` | no | Skip Raspberry Pi detection and other checks on startup. |
| `TALK` | bool | `false` | no | Enable verbose/debug output. |
| `UPLOAD_DIR` | str | `/opt/BotWave/uploads/` | no | Local directory for files to upload to the server. |
| `DOTENV_PATH` | str | `.env` | no | Path to the `.env` file. Must be set before launch to take effect. |
| **Converter** | | | | |
| `CONVERTER_SAMPLE_RATE` | str | `48000` | no | Output sample rate used when converting files to WAV via ffmpeg. |
| `CONVERTER_CHANNELS` | str | `2` | no | Number of output channels used when converting files to WAV. |
| **Backend** | | | | |
| `BACKEND_PATH` | str | *(auto-discovered)* | no | Full path to the backend executable. Searched automatically if unset. |
| `BACKEND_MIN_FREQ` | int | `76` | no | The minimum frequency the backend is able to operate on, in MHz. |
| `BACKEND_MAX_FREQ` | int | `108` | no | The maximum frequency the backend is able to operate on, in MHz. |
| `BACKEND_BYPASS_CACHE` | bool | `false` | no | Set to true to refresh the cached backend path(s). |
| **Resource Monitor** | | | | |
| `RESOURCE_POLL_INTERVAL` | int | `10` | no | How often to check CPU and RAM usage, in seconds. Only active during a broadcast. |
| `RESOURCE_WARN_COOLDOWN` | int | `60` | no | Minimum time between repeated resource warnings, in seconds. |
| `RESOURCE_CPU_THRESHOLD` | int | `80` | no | CPU usage percentage that triggers a warning. |
| `RESOURCE_RAM_THRESHOLD` | int | `90` | no | RAM usage percentage that triggers a warning. |
| **Logging** | | | | |
| `REDACT_IPV4` | bool | `false` | no | Replaces all IPv4 addresses in log output with `[REDACTED]`. |
| `LOG_FILE` | str | *(none)* | no | Path to a file where logs will be written. Disabled if not set. |
| `LOG_TIME` | bool | `false` | no | If `true`, a timestamp is prepended to each log entry. |
| `LOG_TIME_FORMAT` | str | `%Y-%m-%d %H:%M:%S` | no | Timestamp format used when `LOG_TIME` is enabled. |
| **User-Agents** | | | | |
| `VCHECK_UA` | str | `BotWaveVCheck/<version> (+https://github.com/dpipstudio/botwave/)` | no | User-Agent string for version check requests. |
| `DOWNLOAD_UA` | str | `BotWaveDownloads/<version> (+https://github.com/dpipstudio/botwave/)` | no | User-Agent string for file download requests. |