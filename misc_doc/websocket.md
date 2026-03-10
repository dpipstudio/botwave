# BotWave Remote CLI Documentation

## Overview

The BotWave Remote CLI allows clients to connect to the BotWave server to send commands and receive real-time output. It can be used to control a running BotWave instance from any WebSocket-capable tool.

## Connection Details

- **WebSocket URL**: `ws://<server_host>:<rc_port>`
  - `<server_host>`: The hostname or IP address of the BotWave server.
  - `<rc_port>`: The Remote CLI port specified via `--rc` when starting the server.

## Authentication

If a passkey is set on the server, you will be prompted for it immediately after connecting. The server sends a plain-text prompt and expects a plain-text response.

### Flow

```
Server: "Password: "
Client: "your_passkey"
Server: "OK."
Server: "<welcome message, if set>"
```

If no passkey is configured, the server skips straight to `OK.` and you can start sending commands immediately.

### Failure

If the wrong password is provided, the server responds with a plain-text message and closes the connection:

```
Authentication failed.
```

### Timeout

If the client does not respond to the password prompt within the configured timeout (default: 60 seconds, configurable via `REMOTE_CMD_TIMEOUT`), the connection is closed:

```
Authentication timeout.
```

## Commands

Once authenticated, send any BotWave CLI command as a plain-text message. Commands are the same as the interactive shell.

## Example Usage

### Using `websocat`

```bash
websocat ws://localhost:9936
# When prompted:
# Password: your_passkey
# Then type commands normally
```

### Using JavaScript

```javascript
const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:9936');

ws.on('message', function incoming(data) {
  console.log(data);

  if (data === 'Password: ') {
    ws.send('your_passkey');
  }

  if (data === 'OK.') {
    ws.send('lf');
  }
});
```

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `REMOTE_CMD_PORT` | Port for the Remote CLI server | — |
| `REMOTE_BLOCKED_CMD` | Comma-separated list of blocked commands | — |
| `ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING` | Bypass the blocked commands list | `false` |
| `REMOTE_CMD_PWD_TIMEOUT` | Seconds to wait for password input | `60` |
| `REMOTE_CMD_WELCOME` | Message sent to clients after successful auth | — |