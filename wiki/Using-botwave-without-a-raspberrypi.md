This page describes how to install BotWave and use it on a non-raspberry-pi device.

It will only cover the BotWave `client`/`local` component, since the `server` has no special hardware requirements and can be installed on any linux machine following [the existing guide](https://github.com/dpipstudio/botwave/wiki/Setup#installation).

### The Root Cause
Without special settings, the BotWave `client` or `local client` can't start broadcasts without immediately stopping, due to the lack of the hardware the backend requires.

The [`bw_custom`](https://github.com/dpipstudio/bw_custom) backend uses the Raspberry Pi General Purpose Clock output to produce FM on the GPIO 4 pin. Regular computers, or newer Raspberry Pi models don't have this component anymore, thus resulting in the backend stopping when trying to access the device.

If you wish to know more about backends, refer to the [`For Developers/Integrating custom backends`](https://github.com/dpipstudio/botwave/wiki/Integrating-custom-backends) page — this guide will stay high level.

The rest of this tutorial will describe how to use another backend to redirect the audio to another device.

### Installing
Installing BotWave `client` on a regular computer is the exact same process as the regular [installation](https://github.com/dpipstudio/botwave/wiki/Setup#installation). The only different thing is that it'll ask you for install confirmation since it'll detect a non-compatible device.

### Installing Another Backend
As this guide is written, the only other existing backend implementation is [`bw_jack`](https://github.com/douxxtech/bw_jack). Instead of broadcasting audio on FM, it sends it into an [ALSA](https://www.alsa-project.org/wiki/Main_Page) card on your computer.

`bw_jack` isn't installed by the BotWave install script — it's a separate project, written and maintained independently, that you'll need to download and build yourself. That sounds scarier than it is; it's four short steps.

#### 1. Install the dependencies

`bw_jack` is written in C and needs two development libraries to compile: one for talking to ALSA, and one for reading audio files.

```bash
sudo apt install libasound2-dev libsndfile1-dev
```

> [!NOTE]
> If you're not on a Debian/Ubuntu-based system (so `apt` doesn't exist on your machine), install the equivalent packages with your distro's package manager. For example `libasound2-dev` is called `alsa-lib-devel` on Fedora.

#### 2. Get and compile `bw_jack`

```bash
cd /opt/BotWave/backends/
sudo git clone https://github.com/douxxtech/bw_jack
cd bw_jack
gcc bw_jack.c -o bw_jack -lasound -lsndfile
```

If this succeeds, you'll have a new file called `bw_jack` in the folder — that's your compiled backend, ready to be picked up by BotWave.

> [!NOTE]
> Don't have `gcc` or `git`? Install them first with `sudo apt install gcc git`.

#### 3. Point BotWave to it

BotWave caches the backend path after the first successful broadcast, so the first run needs a couple of extra environment variables to force it to pick up `bw_jack` instead of `bw_custom`:

```bash
BACKEND_BYPASS_CACHE=true BACKEND_PATH=/opt/BotWave/backends/bw_jack/bw_jack TALK=true sudo -E bw-local
```

> [!NOTE]
> The `-E` flag on `sudo` tells it to keep your current environment variables instead of resetting them. Without it, the variables above wouldn't reach BotWave once it's running as root.

Once you're in the `botwave >` prompt, start any broadcast, this is what actually makes BotWave lock in the new path:

```bash
start <any audio file>
# or
live
```

> [!TIP]
> After this first broadcast, the path is cached. Future sessions can just use `sudo bw-local`, no environment variables needed.

### You're ready!
Head over to [Main/Basic Usage](https://github.com/dpipstudio/botwave/wiki/Basic-usage) to start broadcasting. Every command you'd normally use (`start`, `live`, `queue`, etc.) works exactly the same way — the only difference is your audio comes out of a sound card instead of over FM, so you won't need an antenna, and you'll want speakers, headphones, or another device plugged into that card to actually hear anything.

> [!NOTE]
> `bw_jack` looks for a sound card named `bcm2835 Headphones` by default (the Raspberry Pi's built-in audio jack), and falls back to `plughw:0,0` if that's not found. On a regular computer, you'll almost always be using that fallback, which is generally your default sound card. If you specifically want to target a different card, you currently have to edit the `DEVICE_NAME` macro near the top of `bw_jack.c` and recompile it. There's no way to pick a card at runtime yet.