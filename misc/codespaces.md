# BotWave Server for GitHub Codespaces

## Intro

Welcome to **BotWave Server for GitHub Codespaces**.
In this tutorial, we will learn how to install and start a server, connect a client, and use the basic commands.

## Additional resources

This tutorial is a recap. For more advanced information, check out these resources:

* [GitHub repo](https://github.com/dpipstudio/botwave)
* [GitHub wiki](https://github.com/dpipstudio/botwave/wiki)
* [Website](https://botwave.dpip.lol)

> **Note:** GitHub Codespaces are ephemeral. Files in `/workspaces` persist during your Codespace session, but the environment is rebuilt when it is stopped. Do not store critical data here.

## Installation

To install BotWave on your GitHub Codespace, make sure you are in the `botwave` directory, then run the following command:

```sh
bash misc_doc/cloud-install.sh
```

This will automatically install all required components.

> **Note:** This can take some time. Do not worry, it hasn't crashed ;)

## Usage

Once the installation is complete, you can start the BotWave server with the following command:

```sh
bw-server
```

If everything works correctly, you should see instructions and a prompt like this:

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

Once your server is running, you can connect one or more clients. Simply run the provided command on a Raspberry Pi.

The client output should look like this:

```terminal
BotWave - Client

[OK] Found bw_custom at: /opt/BotWave/backends/bw_custom/src/bw_custom
[INFO] Checking for protocol updates...
[OK] You are using the latest protocol version
[CLIENT] Connecting to wss://bore.pub:23254...
[OK] WebSocket connected, registering...
[OK] Registered as: tina_127.0.0.1
```

The server should then display:

```terminal
[INFO] Registration attempt from tina
[OK] Client registered: tina (tina_127.0.0.1)
```

## Basic usage

Let us start by looking at the available commands.

Run:

```sh
help
```

A list of available commands will be displayed.

## Download a file

Let us start by downloading a WAV file to broadcast on all clients:

```sh
dl all https://cdn.douxx.tech/files/plasticbeach.wav
```

Expected output:

```terminal
[BCAST] Requesting download from 1 client(s)...
[FILE]   tina (tina_127.0.0.1): Download request sent

[OK] tina (tina_127.0.0.1): Downloaded plasticbeach.wav
```

## Broadcast a file

Now let us broadcast the file we just downloaded on a radio station named **"BWSFGC"** at **90 MHz**, on loop:

```sh
start all plasticbeach.wav 90 true "BWSFGC"
```

Expected output:

```terminal
[BCAST] Starting broadcast ASAP
[BCAST] Starting broadcast on 1 client(s)...
[OK]   tina (tina_127.0.0.1): START command sent
[BCAST] Broadcast start commands sent: 1/1

[OK] tina (tina_127.0.0.1): Broadcasting started
```


## Stopping the broadcast

Once you have had enough, you can stop the broadcast with:

```sh
stop all
```

If you want to stop the server, use the `exit` command.

## Finally
You now know the basics of using BotWave on GitHub Codespaces.
Feel free to explore more possibilities with BotWave!