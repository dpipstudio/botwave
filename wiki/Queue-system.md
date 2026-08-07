The Queue system allows you to manage and play multiple broadcast files in sequence, creating playlists for automatic playback. This is particularly useful for continuous broadcasting without manual intervention.

> [!NOTE]
> The Queue system works in both `server` and `local` instances, with slight differences in behavior.

## Overview

Think of the Queue system as a **playlist manager** for your broadcasts:
- Add files to a queue in the order you want them to play
- Start playback and files will broadcast sequentially
- Each file plays once, then automatically advances to the next
- Pause and resume playback at any time
- In server mode, each client independently tracks its position in the queue

### Key Differences: Server vs Local Mode

| Feature | Server Instance | Local Instance |
|---------|---------------------------|-------------------------|
| Client tracking | Each client has independent queue position | Single position tracker |
| File validation | Checks all clients have the files | Checks local upload directory |
| Target specification | Requires target clients (`all`, `pi1`, etc.) | No targets needed |
| Playback | Multiple clients play simultaneously | Single client playback |

## Queue Command Structure

All queue operations use a single command with different prefixes:

```bash
queue <action><arguments>
```

The action is indicated by a **single character prefix**:

| Action | Symbol | Description |
|--------|--------|-------------|
| Add files | `+` | Add files to the queue |
| Remove files | `-` | Remove files from the queue |
| Show queue | `*` | Display current queue contents |
| Help | `?` | Show queue command help |
| Toggle play/pause | `!` | Start or pause queue playback |

### 1. Adding Files to Queue (`+`)

Add files to your queue in the order you want them to play.

#### Basic Syntax
```bash
queue +<files>
```

#### Examples

**Add a single file:**
```bash
queue +song.wav
```

**Add multiple files (comma-separated):**
```bash
queue +intro.wav,song1.wav,song2.wav,outro.wav
```

**Add all files matching a pattern:**
```bash
queue +music_*.wav
```

**Add all available files:**
```bash
queue +*
```

#### Force Add Mode

In server mode, BotWave checks that all clients have the files before adding them to the queue. If some clients are missing files, the add operation will fail. To bypass this check and add files anyway, use the `!` suffix:

```bash
queue +song.wav!
```

> [!WARNING]
> Force-adding files that don't exist on all clients will cause playback errors when those clients try to broadcast the missing files, that will also cause delays between clients.

<details>
<summary><code>Example: Adding files in server mode</code></summary>
<pre>
botwave> queue +intro.wav,track1.wav,track2.wav
[QUEUE] Added 3 file(s) to queue
[QUEUE] Current queue (3 files):
  1. intro.wav
  2. track1.wav
  3. track2.wav
</pre>
</details>

<details>
<summary><code>Example: Using wildcards</code></summary>
<pre>
botwave> queue +music_*
[QUEUE] Added 5 file(s) to queue
[QUEUE] Current queue (5 files):
  1. music_acoustic.wav
  2. music_electronic.wav
  3. music_jazz.wav
  4. music_rock.wav
  5. music_techno.wav
</pre>
</details>


### 2. Removing Files from Queue (`-`)

Remove files from the queue by index or filename.

#### Basic Syntax
```bash
queue -<files>
```

#### Examples

Usage is the exact same as the [`add`](#1-adding-files-to-queue-).

<details>
<summary><code>Example: Removing files</code></summary>
<pre>
botwave> queue -*
[QUEUE] Removed 2 file(s) from queue
[QUEUE] Queue is empty
</pre>
</details>

### 3. Viewing the Queue (`*`)

Display the current queue contents and playback status.

#### Syntax
```bash
queue *
```

Or simply:
```bash
queue
```

<details>
<summary><code>Example: Viewing queue</code></summary>
<pre>
[QUEUE] Queue (3 files) - PAUSED:
> 1. empty_1.wav (> indicates the file being played)
  2. empty_2.wav
  3. empty_3.wav
</pre>
</details>

### 4. Queue Help (`?`)

Display queue command help and syntax.

#### Syntax
```bash
queue ?
```

<details>
<summary><code>Example output</code></summary>
<pre>
botwave>queue ?
[QUEUE] Queue Commands:
  queue +file                       - Add file to queue
  queue +file1,file2                - Add multiple files
  queue +pattern_*                  - Add files matching pattern
  queue +*                          - Add all files
  queue +file!                      - Force add (skip availability checks)
  queue -file                       - Remove file from queue
  queue -*                          - Clear queue
  queue *                           - Show queue
  queue !                           - Toggle play/pause with defaults
  queue !freq,loop,ps,rt,pi         - Toggle with custom settings
    Example: queue !100.5,false"My Radio","Live",ABCD
</pre>
</details>

### 5. Toggle Play/Pause (`!`)

Start or pause queue playback with optional broadcast settings.

#### Basic Syntax

**Server mode:**
```bash
queue ![targets],[frequency],[loop],[ps],[rt],[pi]
```

**Local mode:**
```bash
queue ![frequency],[loop],[ps],[rt],[pi]
```

> [!TIP]
> All arguments are optional. If not provided, defaults are used:
> * **Targets** (server): `all`
> * **Frequency**: `90.0` MHz
> * **Loop**: `false` (queue plays once then stops)
> * **PS**: `BotWave`
> * **RT**: `Broadcasting`
> * **PI**: `FFFF`

### Examples

**Start queue with defaults:**
```bash
queue !
```

**Server mode, specify targets and frequency:**
```bash
queue !all,88.5
```

**Server mode, full settings:**
```bash
queue !pi1,pi2,95.0,false,MyRadio,"Hit Parade",AAAA
```

**Local mode, frequency and loop:**
```bash
queue !88.5,true
```

**Pause playback:**
```bash
queue !
```
> [!NOTE]
> The `queue !` command toggles between play and pause. If the queue is playing, it pauses. If paused, it resumes, but with default settings.

<details>
<summary><code>Example: Starting queue playback</code></summary>
<pre>
botwave> queue !all,88.5,false,MyRadio,"Queue Mix"
[QUEUE] Queue playing on all
[QUEUE] raspberry: Playing [1/5] intro.wav
[OK]   raspberry (raspberry_192.168.1.96): START command sent
[OK]   raspberry (raspberry_192.168.1.96): Broadcasting started
</pre>
</details> 


## Queue Behavior

### Automatic Advancement

When a file finishes broadcasting:
1. The queue automatically advances to the next file
2. Broadcasting continues without major interruption
3. When the queue reaches the end:
   - **Loop disabled** (`false`): Queue stops and returns to position 0
   - **Loop enabled** (`true`): Queue restarts from the beginning

### Manual Actions Auto-Pause

If you manually start a broadcast using the `start` command while the queue is playing, the queue will automatically pause. This prevents conflicts between manual broadcasts and queued playback.

```bash
botwave ›  start all live.wav 100.0
[QUEUE] Auto-pausing queue due to manual action
[BCAST] Starting broadcast on 1 client(s)...
```

### Multi-Client Independence (Server Mode)

In server mode, each client tracks its own position in the queue:
- Clients can be at different positions in the same queue
- If a client is slower or faster, it won't affect others
- Each client will finish the queue at its own pace

**Example scenario:**
```
Client 1: Playing track 3 of 5
Client 2: Playing track 2 of 5
Client 3: Playing track 4 of 5
```

---

## TL;DR

The Queue system is your tool for automated, sequential broadcasting:

| Command | Purpose | Example |
|---------|---------|---------|
| `queue +` | Add files | `queue +intro.wav,song.wav` |
| `queue -` | Remove files | `queue -*` |
| `queue *` | Show queue | `queue *` |
| `queue ?` | Get help | `queue ?` |
| `queue !` | Play/pause | `queue !all,88.5,false,Radio,Mix` |

**Remember:**
- Add files before playing
- Queue advances automatically after each file
- Manual actions pause the queue
- Each client tracks its own position (server mode)
- Use loop mode for continuous broadcasting