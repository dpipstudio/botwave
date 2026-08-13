The [automatic install script](https://github.com/dpipstudio/botwave/wiki/Setup) is the recommended way to install BotWave. This page exists for people who'd rather not pipe a script into `sudo bash`, are on a system the installer doesn't support, or just want to know exactly what ends up on their machine. It's a bit longer, but nothing here is complicated, just a lot of small steps.

> [!NOTE]
> This walks through the same steps `install.sh` does. If at any point something doesn't make sense, the [script itself](https://github.com/dpipstudio/botwave/blob/main/scripts/install.sh) is the source of truth.

## 1. Install system dependencies

BotWave needs Python 3, a few build tools, and `ffmpeg`. On Debian/Ubuntu (including Raspberry Pi OS):

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv python3-dev libsndfile1-dev libasound2-dev libffi-dev libssl-dev build-essential make ffmpeg git curl jq
```

<details>
<summary>Fedora / dnf</summary>
<hr>

```bash
sudo dnf install -y python3 python3-pip python3-devel libsndfile-devel alsa-lib-devel libffi-devel openssl-devel gcc make ffmpeg git curl jq
```
<hr>
</details>

<details>
<summary>Arch / pacman</summary>
<hr>

```bash
sudo pacman -Sy --noconfirm python python-pip libsndfile alsa-lib libffi openssl base-devel ffmpeg git curl jq
```
<hr>
</details>

## 2. Get the source

Pick a release from the [Releases page](https://github.com/dpipstudio/botwave/releases), or grab the latest `main` branch if you want to live on the edge. We'll install to `/opt/BotWave`, the same place the automatic installer uses.

```bash
sudo mkdir -p /opt/BotWave
cd /opt/BotWave
sudo git clone https://github.com/dpipstudio/botwave.git src
cd src
sudo git checkout v1.2.2-icuria # replace with the release you want, or skip this line for main
```

> [!TIP]
> You don't have to use `/opt/BotWave`. However, if you decide not to, be sure to update `UPLOAD_DIR` and `HANDLERS_DIR` accordingly when starting a BotWave instance.

## 3. Create the directory structure

```bash
cd /opt/BotWave
sudo mkdir -p uploads handlers scripts bin backends client local server shared
```

## 4. Set up the Python virtual environment

```bash
sudo python3 -m venv venv
sudo ./venv/bin/pip install --upgrade pip
```

Now install the Python requirements. Which ones you need depends on what you're installing:

<details>
<summary><strong>Client</strong> (Raspberry Pi that broadcasts)</summary>
<hr>

```bash
sudo ./venv/bin/pip install piwave==2.1.14
```
<hr>
</details>

<details>
<summary><strong>Server</strong> (central machine managing Pis)</summary>
<hr>

```bash
sudo ./venv/bin/pip install cryptography==36.0.2
```
<hr>
</details>

Both client and server also need the common requirements:

```bash
sudo ./venv/bin/pip install \
    websockets==11.0.3 \
    dlogger==1.0.5 \
    aiofiles==0.8.0 \
    aiohttp \
    morse-talk==0.2 \
    pyalsaaudio==0.11.0 \
    psutil==7.2.2 \
    prompt_toolkit==3.0.52
```

> [!NOTE]
> These version numbers can drift as BotWave gets updated. If you're not installing from the same release referenced above, double check [`assets/installation.json`](https://github.com/dpipstudio/botwave/blob/main/assets/installation.json) for the exact list your version expects.

## 5. Copy the files over

This part is pretty straight-forward. Simply copy the content from the `client`, `local`, `server`, and `shared` folders into their corresponding directories.

> [!INFO]
> If you wish to only install a specific component, omit the other directories. However, be sure to always include the `shared` one.

```bash
sudo cp -r src/client/* client/
sudo cp -r src/local/* local/
sudo cp -r src/server/* server/
sudo cp -r src/shared/* shared/
```

## 6. Install the backend (client only)

If you're setting up a client, BotWave also needs the `bw_custom` backend, which handles the actual audio work.

```bash
cd /opt/BotWave/backends
sudo git clone https://github.com/dpipstudio/bw_custom.git
cd bw_custom/src
sudo make
```

## 7. Set up the `bin/` wrappers

Copy the binaries you need from [`bin/`](https://github.com/dpipstudio/botwave/tree/main/bin) into `/opt/BotWave/bin/`, make them executable, and symlink them so you can call them from anywhere:

```bash
cd /opt/BotWave
sudo cp src/bin/* bin/

sudo chmod +x bin/*
sudo ln -sf /opt/BotWave/bin/* /usr/local/bin/
```

Only copy the ones that match your setup (`bw-local`/`bw-client` for a client, `bw-server` for a server), but `bw-autorun`, `bw-nandl`, and `bw-update` are used regardless of mode.


## 8. (Optional) Set up the ALSA loopback card

Only needed if you plan to use [live broadcasting](https://github.com/dpipstudio/botwave/wiki/Live-broadcasting). If you're just playing audio files, skip this, you can always come back to it later.

```bash
sudo tee /etc/modules-load.d/aloop.conf > /dev/null <<EOF
snd-aloop
EOF

sudo tee /etc/modprobe.d/aloop.conf > /dev/null <<EOF
options snd-aloop index=10 id=BotWave pcm_substreams=1,1
EOF
```

> [!WARNING]
> You need to **reboot** for this to take effect.

## 9. Save version info

This step is optional, but recommended: BotWave uses this to check for updates and to show you what version you're running. Skipping it just means those checks won't work.

```bash
cd /opt/BotWave
echo "v1.2.2-icuria" | sudo tee last_release # replace with your release
# or, if you installed from a commit instead of a release:
# echo "<commit-sha>" | sudo tee last_commit
```

## 10. You're ready!

Start your client or server the same way you would with a normal install:

```bash
sudo bw-local # single Pi
# or
bw-server # central machine
sudo bw-client <server-ip> # Pi connecting to a server
```

If everything's in place, you'll see the usual `botwave >` prompt. From here, head to [Main/Basic Usage](https://github.com/dpipstudio/botwave/wiki/Basic-usage) to start broadcasting, or back to [Base/Setup](https://github.com/dpipstudio/botwave/wiki/Setup) if you got stuck and want to compare against the automatic install path.