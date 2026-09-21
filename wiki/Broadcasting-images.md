This page documents how to broadcast images over sound on FM radio using BotWave.

To achieve this, BotWave supports SSTV generation and broadcast.

SSTV, or slow-scan television, is a way of transmitting images using sound signals. It was first introduced by Copthorne Macdonald in 1957-58.

### Installing
SSTV dependencies are not installed by default. This means you'll have to install them manually before starting an SSTV broadcast.

> [!WARNING]
> This may take some time and will triple the base-install disk size.

```bash
sudo /opt/BotWave/venv/bin/pip install pysstv numpy pillow
```

### Running
This example shows how to start an SSTV broadcast on the `local` component. The process is the same for the `server` one.

Start by launching a BotWave instance and, optionally, downloading an image:
```bash
sudo bw-local

[...]

botwave › < curl -O https://images.dpip.lol/bw-logo.png
```

Then simply start a broadcast using the SSTV command:

```bash
botwave › # command syntax: sstv <image_path> [mode] [frequency] [loop] [ps] [rt] [pi]
botwave › sstv bw-logo.png
[SSTV] Generating SSTV WAV from bw-logo.png using mode auto...
[SSTV] SSTV wav created /tmp/botwave/bw_sstv/79193160a088ed10.wav (mode: PD160)
[OK] Started broadcasting /tmp/botwave/bw_sstv/79193160a088ed10.wav on 90MHz
```

You can choose an encoding mode using the mode positional argument. All available modes can be found [here](https://github.com/dnet/pysstv).

If the mode is left empty, BotWave will automatically choose the best mode based on the image you provided.

```bash
botwave › # using the "Robot36" mode on 99Mhz
botwave › sstv bw-logo.png Robot36 99
[SSTV] Generating SSTV WAV from bw-logo.png using mode Robot36...
[SSTV] SSTV wav created /tmp/botwave/bw_sstv/0d97b7d07378290b.wav (mode: Robot36)
[OK] Started broadcasting /tmp/botwave/bw_sstv/0d97b7d07378290b.wav on 99.0MHz
```

### Decoding the image
To decode the image, you can use a tool like [Robot36](https://github.com/xdsopl/robot36/), available on the Google Play Store. Simply tune a radio to the broadcast frequency and start the app to decode the image.

<div align="center">
    <img src="https://images.dbo.one/57e8c3c8" alt="output" width="400" />
</div>