# BotWave WebSocket API Documentation

## Overview

The BotWave WebSocket API allows clients to connect to the BotWave server to send and receive real-time messages. This API is used for monitoring and controlling the BotWave server remotely.

## Connection Details

- **WebSocket URL**: `ws://<server_host>:<ws_port>`
  - `<server_host>`: The hostname or IP address of the BotWave server.
  - `<ws_port>`: The WebSocket port specified when starting the BotWave server.

## Authentication

Clients must authenticate with the server upon connecting. If a passkey is set on the server, it must be provided during authentication.

### Authentication Message

```json
{
  "type": "auth",
  "passkey": "your_passkey"
}
```

### Authentication Response

- **Success**:
  ```json
  {
    "type": "auth_ok",
    "message": "Authenticated"
  }
  ```

- **Failure**:
  ```json
  {
    "type": "auth_failed",
    "message": "Invalid passkey"
  }
  ```

## Commands

Once authenticated, clients can send commands to the server. Commands are the same than the CLI version.

## Example Usage

Here is an example of how to connect and interact with the BotWave WebSocket API using JavaScript:

```javascript
const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:9936');

ws.on('open', function open() {
  ws.send(JSON.stringify({
    type: 'auth',
    passkey: 'your_passkey'
  }));
});

ws.on('message', function incoming(data) {
  const message = JSON.parse(data);
  console.log('Received:', message);

  if (message.type === 'auth_ok') {
    ws.send('list');
  }
});
```

## Error Handling

- **Authentication Timeout**: If the client does not authenticate within 5 seconds, the connection will be closed.
- **Invalid Commands**: If an invalid command is sent, an error message will be returned.

Example error message:

```json
{
  "type": "error",
  "message": "Unknown command: invalid_command"
}
```