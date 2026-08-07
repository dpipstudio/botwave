This page explains how to broadcast live audio through BotWave, meaning audio streamed in real time rather than from a pre-recorded file.

> [!NOTE]
> This page assumes you're already familiar with the basics. If not, start with [Main/Basic Usage](https://github.com/dpipstudio/botwave/wiki/Basic-usage).



## How it works

Live broadcasting in BotWave uses an **ALSA loopback card**. It is a virtual audio device on your system that acts as a bridge. You send audio into it from any application, and BotWave picks it up and transmits it over FM. Think of it like a virtual cable between your audio source and the radio transmitter.

> [!IMPORTANT]
> You need the ALSA loopback card installed for live broadcasting to work. If you skipped it during installation, you can enable it by re-running the installer with the `--alsa` flag:
> ```bash
> curl -sSL https://botwave.dpip.lol/install | sudo bash -s -- client --alsa
> ```
> Then verify it's available by running `aplay -l` — you should see two `BotWave` cards listed.



## Starting a Live Broadcast

Once your ALSA card is set up, starting a live broadcast is straightforward. In your BotWave prompt, type `live`:

**Local Client:**
```bash
botwave> live [frequency] [ps] [rt] [pi]
```

**Server:**
```bash
botwave> live <targets> [frequency] [ps] [rt] [pi]
```

| Parameter | Description |
|--|-|
| `targets` | (server only) Client ID, hostname, or `all` |
| `frequency` | FM frequency in MHz (default: `90.0`) |
| `ps` | Station name shown on RDS radios (default: `BotWave`) |
| `rt` | Station description (default: `Broadcasting`) |
| `pi` | Program Identifier code (default: `FFFF`) |

**Example:**
```bash
botwave> live 88.5 MyRadio "Live Show"
```

Once the command runs, BotWave is listening on the ALSA loopback card. Now you just need to send audio to it.


## Sending Audio to BotWave

The ALSA card expects audio in this format: **48000 Hz, 2 channels, S16_LE**. Any source that can output in this format will work.

### Playing a local file

This is useful for streaming files to clients without storing them on their filesystem first:

```bash
aplay -D plughw:BotWave,0 yourfile.wav
```

### Using a microphone

1. Find your microphone's card name:
   ```bash
   arecord -l
   ```

2. Pipe its audio into BotWave:
   ```bash
   arecord -D plughw:YOUR_CARD,0 -f S16_LE -c 2 -r 48000 | aplay -D plughw:BotWave,0
   ```
   Replace `YOUR_CARD` with your microphone's card name or number from the previous step.



## Streaming from Another Device

This section covers how to stream audio from a separate computer to the Pi running BotWave. Both machines need [FFmpeg](https://ffmpeg.org/) installed.

### From a Linux or Mac computer

On the **Pi**, start listening for incoming audio:
```bash
ffmpeg -f s16le -ac 2 -ar 48000 -i udp://0.0.0.0:5004 -f alsa plughw:BotWave,0
```

On your **Linux or Mac computer**, send audio from your system output. First find your output device:
```bash
# Linux (PulseAudio)
pactl list short sources

# Mac
ffmpeg -list_devices true -f avfoundation -i dummy
```

Then stream it:
```bash
# Linux (PulseAudio) - replace with your source name
ffmpeg -f pulse -i your_monitor_source -ac 2 -ar 48000 -f s16le udp://PI_HOST:5004

# Mac - replace with your device index
ffmpeg -f avfoundation -i ":DEVICE_INDEX" -ac 2 -ar 48000 -f s16le udp://PI_HOST:5004
```

Replace `PI_HOST` with your Pi's IP address.



### From a Windows computer

This uses [VoiceMeeter](https://vb-audio.com/Voicemeeter/) to capture your system audio and FFmpeg to stream it.

#### Windows setup

1. Install [VoiceMeeter](https://vb-audio.com/Voicemeeter/)
2. Open VoiceMeeter and in the **VIRTUAL INPUT** section:
   - Disable the `>A` button
   - Enable the `>B` button
3. Set your system audio output to `VoiceMeeter Input (VB-Audio Voicemeeter VAIO)`
4. Verify FFmpeg can see it:
   ```bash
   ffmpeg -list_devices true -f dshow -i dummy
   ```
   You should see `Voicemeeter Out B1 (VB-Audio Voicemeeter VAIO)` in the list.

#### Pi setup

On the Pi, start listening:
```bash
ffmpeg -f s16le -ac 2 -ar 48000 -i udp://0.0.0.0:5004 -f alsa plughw:BotWave,0
```

#### Stream from Windows

```bash
ffmpeg -f dshow -i audio="Voicemeeter Out B1 (VB-Audio Voicemeeter VAIO)" -ac 2 -ar 48000 -f s16le udp://PI_HOST:5004
```

Replace `PI_HOST` with your Pi's IP address.

> Expect around 5 seconds of latency depending on your network. The transmission speed should stabilize around `1x` after a few seconds. If it doesn't, restart both FFmpeg commands.


## Troubleshooting

**The `live` command fails or nothing transmits:**
- Run `aplay -l` and confirm a `BotWave` card is listed. If not, re-run the installer with `--alsa`.

**Audio is silent or cuts out:**
- Make sure your source is outputting at **48000 Hz, 2 channels, S16_LE**. Mismatched formats are the most common cause of silence.

**FFmpeg stream is too fast or too slow:**
- Restart both FFmpeg commands (Pi side first, then computer side). This usually stabilizes within a few seconds.

**Still stuck?** Check the [FAQ](https://github.com/dpipstudio/botwave/wiki/FAQ) or open an issue [here](https://github.com/dpipstudio/botwave/issues/new).