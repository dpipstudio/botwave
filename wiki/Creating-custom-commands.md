This page documents how to write and use BotWave's custom commands.

### What *Is* a Custom Command?

A custom command is a [handler](https://github.com/dpipstudio/botwave/wiki/Automate-your-setup) with a few key differences.

Like regular handlers, custom command files live in the handlers directory (`/opt/BotWave/handlers` by default). But instead of a `.hdl` or `.shdl` extension, they use `.cmd`, this keeps them visually distinct from event-driven handlers.

The **first line** of every custom command file must be a shebang in this format:

```
#!/<server|local|*>/<command_name>
```

- `server` makes the command available in `bw-server`, `local` in `bw-local`. Use * to make it available in both.
- `<command_name>` is the command's name as typed in the prompt. It must match the filename (without the extension).

BotWave hot-reloads `.cmd` files automatically, re-checking the handlers directory on every command run, so no restart is needed after creating or editing one.

### Creating Your First Custom Command
> In this part, we'll assume you have a Linux machine with BotWave server installed.

Let's start with a simple example. Create `/opt/BotWave/handlers/hello.cmd`:

```bash
sudo nano /opt/BotWave/handlers/hello.cmd
```

```
#!/*/hello
# hello <word>
#   Prints "Hello, <word>" with word as the first arg passed

< echo Hello, {BW_ARGV1}
```

In this example:

- The shebang on line 1 registers this as a command named `hello`, available on both the local client and the server (`*`).
- The `#` block right after it is the **help text**. BotWave reads the first consecutive `#` block and uses it in the `help` command output. This block is optional but strongly recommended.
- `<` runs its arguments in a shell and prints the output.
- `{BW_ARGV1}` is replaced at runtime with the first argument passed to the command. `BW_ARGV{n}` variables are 0-indexed, but `BW_ARGV1` is the first *user-supplied* argument, not the command name itself (`BW_ARGV0`).

After saving, the command is immediately available:

```bash
:3 $ help
[...]
 Custom Commands ─────────────────

 hello <word>
   Prints "Hello, <word>" with word as the first arg passed
[...]

:3 $ hello world

Hello, world
:3 $ hello "kitty kitty kitty"

Hello, kitty kitty kitty
```


### Using More Complex Setups

One-liners work fine for simple cases, but the moment you need conditionals, loops, or proper error handling, it's cleaner to delegate to a shell script and use the `.cmd` file purely as a *bridge*:

`/opt/BotWave/handlers/hello.cmd`:
```
#!/*/hello
# hello <word>
#   Prints "Hello, <word>" with word as the first arg passed

< bash /opt/BotWave/scripts/hello.sh
```

`/opt/BotWave/scripts/hello.sh`:
```bash
#!/bin/bash

if [[ -z "$BW_ARGV1" ]]; then
    echo "Syntax: hello <word>"
    exit
fi

echo "Hello, $BW_ARGV1"
```

Since BotWave exposes `BW_ARGV{n}` as real environment variables, your shell script can access them directly, no special syntax needed there.

```bash
:3 $ hello

Syntax: hello <word>
:3 $ hello :3

Hello, :3
```

### Using The Pipe Command

An alternative to `<` is the pipe command (`|`). Like `<`, it runs its argument in a shell, but instead of printing the output, it re-runs **each output line as a BotWave command**.

This is useful when you want a script to *generate* commands dynamically rather than just producing text. For example, a whitelist check that kicks unauthorized clients:

**`/opt/BotWave/scripts/whitelist.sh`**:
```bash
#!/bin/sh
WHITELIST="pi pi1 radpi"
FOUND=0

for h in $WHITELIST; do
    if [ "$h" = "$BW_CLIENT_HOSTNAME" ]; then
        FOUND=1
        break
    fi
done

if [ "$FOUND" -ne 1 ]; then
    echo "kick ${BW_CLIENT_HOSTNAME} \"Not on whitelist\""
fi
```

`/opt/BotWave/handlers/wl.cmd`:
```
#!/server/wl
# wl
#   Runs the whitelist script

| sh /opt/BotWave/scripts/whitelist.sh
```

Each line the script prints gets executed as a BotWave command. In this case, if the client isn't on the whitelist, the script outputs a `kick` command, which BotWave then runs.

You can also use it for something as simple as feeding a command list from a file:

```
| cat commands.txt
```