# BotWave Server For Google Shell

## Intro

Welcome to BotWave Server For Google Shell.  
In this tutorial, we'll see how to install and start a server, how to connect a client, and basic commands.

### Additional ressources

Of course, this tutorial will be a recap, to find more advanced informations, here are some ressources:

- [Github repo](https://github.com/dpipstudio/botwave)
- [Github wiki](https://github.com/dpipstudio/botwave/wiki)
- [Website](https://botwave.dpip.lol)

> Google shells are ephemeral. Every created file will be deleted once your session end. Don't store important files.

## Installation

To install BotWave on your Google Shell, please be sure to be in the `botwave` directory, and run the following command:

```sh
bash misc_doc/cloud-install.sh
```

It should automatically install all required components.
> Note: This can take some time, don't worry, it didn't crash ;)

## Usage

Once installed successfully, you should be able to run botwave server with the following command.

```sh
bw-server
```

If everything goes well, you should be able to see some instructions and a prompt, like here.

```terminal
BotWave - Server

[TLS] Generated self-signed TLS certificate
[SERVER] WebSocket server started on wss://0.0.0.0:9938
[SERVER] HTTP file server started on https://0.0.0.0:9921
[SERVER] BotWave Server started
[VER] Protocol Version: 2.0.0
[INFO] Checking for protocol updates...
[OK] You are using the latest protocol version
Type 'help' for commands
==========================================
BotWave Server Started!
==========================================

Launching tunnels, please wait.
Starting bore.pub tunnels...
This will expose your BotWave server to the internet.


==========================================
WebSocket: bore.pub:23254 (local 9938)
HTTP:      bore.pub:28401 (local 9921)
==========================================

Connect with: sudo bw-client bore.pub --port 23254 --fport 28401

==========================================

botwave ›  
```

## Connecting a client

Once your server launched, you'll be able to connect one or multiple clients. Simply launch the given command on a raspberry pi.  
The output should be the following:
```terminal
BotWave - Client

[OK] Found bw_custom at: /opt/BotWave/backends/bw_custom/src/bw_custom
[INFO] Checking for protocol updates...
[OK] You are using the latest protocol version
[CLIENT] Connecting to wss://bore.pub:23254...
[OK] WebSocket connected, registering...
[OK] Registered as: tina_127.0.0.1
```

The server should show this.
```terminal
[INFO] Registration attempt from tina
[OK] Client registered: tina (tina_127.0.0.1)
```

## Basic usage

Let's start by taking a look at the commands.
Run
```sh
help
```

A list of availble commands will be shown.

## Download a file
Let's start by download a wav file to broadcast on all clients.

```sh
dl all https://cdn.douxx.tech/files/plasticbeach.wav
```

Here is the excpected output:
```terminal
[BCAST] Requesting download from 1 client(s)...
[FILE]   tina (tina_127.0.0.1): Download request sent

[OK] tina (tina_127.0.0.1): Downloaded plasticbeach.wav
```

## Broadcast a file
Let's broadcast the file we just downloaded, on a radio named "BWSFGS" on 90MHz, on loop.

```sh
start all plasticbeach.wav 90 true "BWSFGS"
```

Excpected output:
```terminal
[BCAST] Starting broadcast ASAP
[BCAST] Starting broadcast on 1 client(s)...
[OK]   tina (tina_127.0.0.1): START command sent
[BCAST] Broadcast start commands sent: 1/1

[OK] tina (tina_127.0.0.1): Broadcasting started
```


## Stopping the broadcast
Once we had enough, let's stop this broadcast.

```sh
stop all
```

Additionally, if you want to stop the server, use the `exit` command.


## Finally
Now you know the basic usage of BotWave on Google Shell.  
Feel free to explore more possibilites with BotWave !
