In this page you'll learn what a backend is, how BotWave uses it, and how to build or plug in your own.

> [!NOTE]
> This page is aimed at developers who want to change *how* BotWave outputs audio. If you just want to broadcast FM normally, you don't need any of this.

## What is a backend?

When BotWave tells a client to broadcast, it doesn't do the actual audio transmission itself. It delegates that job to a small external program called a **backend**. Think of it as the engine under the hood: BotWave decides *what* to play and *when*, and the backend is the thing that actually makes sound come out.

The default backend is [`bw_custom`](https://github.com/dpipstudio/bw_custom), which uses the Raspberry Pi's hardware clock to generate an FM signal on GPIO4. That's great for radio broadcasting, but it's not the only thing you might want to do. Maybe you want to pipe audio to a sound card, a walkie-talkie, a network stream, or something else entirely. That's where custom backends come in.

A backend is just **a binary that accepts a specific set of arguments**. As long as your program speaks the same interface as `bw_custom`, BotWave will use it without any other changes.

## How BotWave invokes the backend

When a broadcast starts, BotWave calls the backend like this:

```
<backend_binary> -freq <MHz> -audio <file|-> [-ps <text>] [-rt <text>] [-pi <hex>] [-loop] [-raw] [-rate <Hz>] [-channels <N>]
```

That's it. BotWave calls the binary, passes arguments, and the backend is responsible for everything else. It reads the audio (either from a file or from stdin in `-raw` mode) and does whatever it wants with it.

The backend runs as a subprocess. When BotWave receives a `stop` command, it kills that process.

### Arguments BotWave may pass

| Flag | Description |
|---|---|
| `-freq <MHz>` | FM frequency. Required by `bw_custom`, but you can ignore it if your backend doesn't broadcast FM. |
| `-audio <path\|->` | Path to a WAV file, or `-` to read raw PCM from stdin. |
| `-ps <text>` | RDS station name (max 8 chars). Optional. |
| `-rt <text>` | RDS radio text (max 64 chars). Optional. |
| `-pi <hex>` | RDS Programme Identifier code. Optional. |
| `-loop` | Loop the audio indefinitely. |
| `-raw` | Audio input is raw S16LE PCM from stdin. |
| `-rate <Hz>` | Sample rate for raw PCM input. |
| `-channels <N>` | Channel count for raw PCM input. |

> [!TIP]
> You don't need to support all of these. If your backend doesn't care about `-freq` or `-ps`, just ignore them. BotWave will still pass them, but as long as your program doesn't crash on unknown flags, you're fine.

## Registering a custom backend

BotWave caches the path to the backend binary so it doesn't have to search for it on every broadcast. To point it at your binary, you use two environment variables at startup:

- `BACKEND_BYPASS_CACHE=true`: tells BotWave to ignore its cached path and look for a new one.
- `BACKEND_PATH=<path>`: the full path to your backend binary.

Run `bw-local` with both:

```bash
BACKEND_BYPASS_CACHE=true BACKEND_PATH=/opt/BotWave/backends/mybak/mybak TALK=true sudo -E bw-local
```

Once the shell opens, **trigger a broadcast** (any file will do):

```
botwave> start myfile.wav
```

That's enough for BotWave to register and cache the new path. From that point on, you can run `sudo bw-local` normally and it will use your backend automatically.

> [!NOTE]
> The `TALK=true` flag is optional but recommended the first time. It prints extra debug output so you can confirm the right binary is being picked up.


## Example: bw_jack

[`bw_jack`](https://github.com/douxxtech/bw_jack) is a community backend that routes audio to an ALSA/JACK sound card instead of broadcasting FM. It was originally built to pipe audio into a walkie-talkie, but it works with anything ALSA can talk to.

It's a good real-world example of how minimal a custom backend can be: it accepts the same arguments as `bw_custom`, ignores the ones it doesn't need (like `-freq`), and just plays audio through the system's audio output.

### Building it

```bash
sudo apt install libasound2-dev libsndfile1-dev
git clone https://github.com/douxxtech/bw_jack.git
cd bw_jack
gcc bw_jack.c -o bw_jack -lasound -lsndfile
```

### Installing it

```bash
sudo mkdir -p /opt/BotWave/backends/bw_jack
sudo cp bw_jack /opt/BotWave/backends/bw_jack/bw_jack
```

### Registering it with BotWave

```bash
BACKEND_BYPASS_CACHE=true BACKEND_PATH=/opt/BotWave/backends/bw_jack/bw_jack TALK=true sudo -E bw-local
```

Then start any broadcast from the shell. 

## Writing your own backend

The interface is intentionally simple. Here's the minimum your backend needs to do:

1. **Accept `-audio <path>` or `-audio -` with `-raw`**, this is how BotWave passes audio to your binary.
2. **Exit cleanly when killed**: BotWave sends SIGTERM when a broadcast is stopped. Make sure you handle it.
3. **Not crash on unknown flags**: BotWave may pass `-freq`, `-ps`, `-rt`, `-pi`, etc. even if your backend doesn't use them.

Everything else is up to you. Your backend can be written in C, Python, Go, Bash, or anything that produces an executable. As long as BotWave can call it and kill it, it works.

For a real reference implementation, look at [`bw_custom`'s source](https://github.com/dpipstudio/bw_custom/tree/main/src) (the official backend) or [`bw_jack`'s source](https://github.com/douxxtech/bw_jack/blob/main/bw_jack.c) (a simpler community example).

## Switching back to the default backend

If you want to go back to `bw_custom`, just re-register it the same way:

```bash
BACKEND_BYPASS_CACHE=true BACKEND_PATH=/opt/BotWave/backends/bw_custom/src/bw_custom sudo -E bw-local
```

Or, if BotWave is on the default installation path, you can also just unset `BACKEND_PATH` and set `BACKEND_BYPASS_CACHE=true`. BotWave will auto-discover `bw_custom` from its known locations and re-cache it.