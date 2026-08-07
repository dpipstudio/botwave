This page covers how to build tools and scripts that talk to BotWave programmatically over the WebSocket remote shell, and how to use the `transaction_id` feature to reliably collect responses.

> [!NOTE]
> This page assumes you already have the remote shell enabled and working. If not, start with [Main/Connecting remotely](https://github.com/dpipstudio/botwave/wiki/Connecting-remotely).

## The basics

Once you've connected to the remote shell, it's just a WebSocket. You send a command as a text message, BotWave executes it, and any log output gets forwarded back to you in real time.

That works great for fire-and-forget commands like `start mysong.wav 90.5` or `stop`. But the moment you want to **read** something, like the current status, the file list, the queue, you run into a problem: how do you know which log lines are the response to *your* command, and not just ambient noise from something else happening on the Pi?

This is where `transaction_id` comes in.

## transaction_id

Every command you send to the remote shell can carry a `transaction_id` tag:

```
status transaction_id=my_request_1
```

BotWave will echo that tag back on every log line that's part of the response to that command:

```
[INFO] On Airtransaction_id=my_request_1
[INFO] File       : mysong.wavtransaction_id=my_request_1
[INFO] Frequency  : 90.5 MHztransaction_id=my_request_1
```

Lines that aren't tagged belong to the general log stream (other events, broadcasts starting, etc.) and can be safely ignored when you're waiting for a specific response.

### How to use it

Append `transaction_id=<anything>` to the end of your command. The value is just a string, so use whatever makes sense for your application:

```
lf transaction_id=filelist_req
queue ? transaction_id=queue_poll_42
status transaction_id=dashboard_refresh
```

> [!NOTE]
> `transaction_id` works with any command. It's not limited to query-type commands. You can tag `start`, `stop`, or anything else if you want to correlate their output.

### End marker

When BotWave finishes processing a tagged command, it sends a dedicated end marker:

```
ENDtransaction_id=my_request_1
```

This is a log that signals the command's output is fully flushed.

### Collecting the response

Listen for tagged lines and resolve once you see the end marker. [BWSC](https://github.com/douxxtech/bwsc) uses exactly this pattern in its `--command` mode:

```js
generateTransactionId() {
    return `bwsc_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

async runCommand(command) {
    const txId = this.generateTransactionId();
    const taggedCommand = `${command} transaction_id=${txId}`;
    const endMarker = `ENDtransaction_id=${txId}`;

    return new Promise((resolve) => {
        const output = [];
        const originalHandle = this.handleMessage.bind(this);

        this.handleMessage = (message) => {
            if (message.includes(txId)) {
                if (message.trim() === endMarker) {
                    this.handleMessage = originalHandle;
                    this.ws.close(1000, 'done');
                    this.ws.on('close', () => resolve(output));
                    return;
                }

                output.push(message);
                const cleaned = message.replace(`transaction_id=${txId}`, '').trimEnd();
                console.log(this.colorizeMessage(cleaned));
            }
        };

        this.ws.send(taggedCommand);
    });
}
```

Once the end marker arrives, the promise resolves with everything collected. No timers, no guessing.

You can use BWSC's `--command` mode directly from the shell to query BotWave without writing any code:

```bash
bwsc 192.168.1.10 --command "status"
bwsc 192.168.1.10 --command "lf"
```

## Parsing responses

BotWave log lines follow a consistent format:

```
[TAG] Message content
```

Where `TAG` is something like `INFO`, `OK`, `ERR`, `BCAST`, `FILE`, etc. Strip the tag prefix before processing:

```js
function stripTag(line) {
    return line
        .replace(/^\[[A-Z]+\]\s/, '')
        .replace(/\s*transaction_id=[^\s]+/, '')
        .trim();
}
```

From there, use simple string matching or regex on the content. For example, parsing `status` output:

```js
const lines = await query(ws, 'status');

for (const line of lines) {
    const clean = stripTag(line);

    if (clean.includes('On Air')) onAir = true;
    if (clean.includes('Idle')) onAir = false;

    const freqM = clean.match(/Frequency\s*:\s*([\d.]+)/);
    if (freqM) freq = freqM[1];

    const fileM = clean.match(/File\s*:\s*(.+)/);
    if (fileM) file = fileM[1].trim();
}
```

And for `lf` (file list):

```js
const lines = await query(ws, 'lf');
const files = [];

for (const line of lines) {
    const clean = stripTag(line).trim();
    if (clean && !clean.startsWith('Files in') && !clean.startsWith('No files')) {
        files.push(clean);
    }
}
```

## Example: a simple polling dashboard (Node.js)

Here's a minimal but complete example that connects, authenticates, and polls BotWave every few seconds to print the current status.

```js
const WebSocket = require('ws');

const HOST = 'ws://192.168.1.10:9939';
const PASSKEY = 'MyRemotePass';

async function connect() {
    const ws = new WebSocket(HOST);

    await new Promise((res, rej) => {
        ws.on('open', res);
        ws.on('error', rej);
    });

    // auth handshake
    await new Promise((res, rej) => {
        ws.on('message', function handler(data) {
            const msg = data.toString().trim();
            if (msg === 'Password:') ws.send(PASSKEY);
            else if (msg === 'OK.') { ws.removeListener('message', handler); res(); }
            else if (msg.startsWith('Authentication')) rej(new Error(msg));
        });
        if (!PASSKEY) res();
    });

    return ws;
}

async function query(ws, command) {
    const txId = `poll_${Date.now()}`;
    const endMarker = `ENDtransaction_id=${txId}`;

    return new Promise((resolve) => {
        const lines = [];

        function handler(data) {
            const raw = data.toString();
            if (!raw.includes(txId)) return;

            if (raw.trim() === endMarker) {
                ws.removeListener('message', handler);
                resolve(lines);
                return;
            }

            lines.push(raw.replace(/\s*transaction_id=\S+/, '').trim());
        }

        ws.on('message', handler);
        ws.send(`${command} transaction_id=${txId}`);
    });
}

function stripTag(line) {
    return line.replace(/^\[[A-Z]+\]\s/, '').trim();
}

async function main() {
    const ws = await connect();
    console.log('Connected.');

    setInterval(async () => {
        const lines = await query(ws, 'status');
        let onAir = false, freq = null, file = null;

        for (const line of lines) {
            const c = stripTag(line);
            if (c.includes('On Air')) onAir = true;
            const fm = c.match(/Frequency\s*:\s*([\d.]+)/);
            if (fm) freq = fm[1];
            const nm = c.match(/File\s*:\s*(.+)/);
            if (nm) file = nm[1].trim();
        }

        console.log(`[${new Date().toLocaleTimeString()}] ${onAir ? '◉ ON AIR' : '○ IDLE'} ${freq ? freq + ' MHz' : ''} ${file || ''}`);
    }, 3000);
}

main().catch(console.error);
```

## Example: Python

Same idea, but with `websockets` (async):

```py
import asyncio
import re
import time
import websockets

HOST = "ws://192.168.1.10:9939"
PASSKEY = "MyRemotePass"

async def connect():
    ws = await websockets.connect(HOST)

    if PASSKEY:
        msg = await ws.recv()
        if msg.strip() == "Password:":
            await ws.send(PASSKEY)
        msg = await ws.recv()
        if msg.strip() != "OK.":
            raise Exception(f"Auth failed: {msg}")

    return ws

async def query(ws, command):
    tx_id = f"py_{int(time.time() * 1000)}"
    end_marker = f"ENDtransaction_id={tx_id}"
    lines = []

    await ws.send(f"{command} transaction_id={tx_id}")

    async for raw in ws:
        if f"transaction_id={tx_id}" not in raw:
            continue
        if raw.strip() == end_marker:
            break
        clean = re.sub(r'\s*transaction_id=\S+', '', raw).strip()
        lines.append(clean)

    return lines

def strip_tag(line):
    return re.sub(r'^\[[A-Z]+\]\s', '', line).strip()

async def main():
    ws = await connect()
    print("Connected.")

    while True:
        lines = await query(ws, "status")
        on_air = False
        freq = file = None

        for line in lines:
            c = strip_tag(line)
            if "On Air" in c:
                on_air = True
            m = re.search(r'Frequency\s*:\s*([\d.]+)', c)
            if m:
                freq = m.group(1)
            m = re.search(r'File\s*:\s*(.+)', c)
            if m:
                file = m.group(1).strip()

        status = "◉ ON AIR" if on_air else "○ IDLE"
        print(f"{status}  {freq + ' MHz' if freq else ''}  {file or ''}")
        await asyncio.sleep(3)

asyncio.run(main())
```

## Sending commands without waiting for a response

Not everything needs a `transaction_id`. For fire-and-forget commands, just send and move on:

```js
ws.send('start mysong.wav 90.5');
ws.send('queue +another.wav');
ws.send('stop');
```

Or via BWSC's `--fire` flag:

```bash
bwsc 192.168.1.10 --fire "start mysong.wav 90.5"
```

The log output from those commands will still arrive via the general message stream. If you have a global message listener, you'll see them, you just won't be able to tie them back to a specific call without the tag.

## Notes

- **No interpolation**: `{VAR}` placeholders are not expanded for commands sent over the remote shell. This is intentional. Don't rely on it.
- **Blocked commands**: `get`, `set`, `<`, and `|` are blocked by default. If your automation needs them, see `ALLOW_REMOTE_BLOCKED_COMMANDS_I_KNOW_WHAT_IM_DOING` in [Main/Connecting remotely](https://github.com/dpipstudio/botwave/wiki/Connecting-remotely).
- **Log mirroring**: All BotWave output is forwarded to every connected client. Your script will receive log lines from broadcasts, other clients connecting, etc. Filter by `transaction_id` to avoid acting on noise.
- **Multiple concurrent queries**: `transaction_id` makes this safe. Each in-flight query has its own ID, so you can fire multiple queries simultaneously without them stepping on each other.