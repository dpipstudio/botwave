# AGENTS.md

Last reviewed: 07/07/2026

Instructions for AI coding agents (Claude Code, Cursor, Copilot, Codex, etc.) working in this repo.

## What this project is

BotWave broadcasts audio over FM radio using Raspberry Pi devices (via GPIO 4 / pin 7), either as a
standalone device (`local`) or as a server managing multiple Pi clients (`server` + `client`). Python 3.9+, no build step, no test suite, see "Testing" below before assuming otherwise.

## Repo layout

| Path | What it is |
| --- | --- |
| `server/server.py` | Server entrypoint (`bw-server`). Manages multiple connected clients. |
| `client/client.py` | Client entrypoint (`bw-client`). Connects a Pi to a server. |
| `local/local.py` | Standalone client entrypoint (`bw-local`). No server needed. |
| `server/ops/`, `client/ops/`, `local/ops/` | One file per CLI command or action/event (`start.py`, `stop.py`, `upload.py`, ...). Add new features here. |
| `shared/` | Code shared across two or more components: protocol (`protocol.py`), env vars (`env.py`), handlers (`handlers.py`), audio conversion (`converter.py`), etc. |
| `autorun/autorun.py` | Manages systemd services for autostart (`bw-autorun`). |
| `bin/` | Thin bash launchers that exec the Python entrypoints from `/opt/BotWave/venv`. This is what an installed system actually calls. |
| `scripts/` | `install.sh`, `update.sh`, `uninstall.sh`: the installer, not typically what you're editing for a feature change. |
| `.github/scripts/` | Release automation. |
| `wiki/` | A wiki mirror. Useful for searching documentation about specific features. |
| `misc/` | Miscellaneous stuff. |

Full per-component docs (all CLI flags, all commands, all handler hooks) live in:
`server/server.md`, `client/client.md`, `local/local.md`, `autorun/autorun.md`. Read the relevant one before changing that component's CLI surface, this file intentionally stays high-level.

Deeper guides (setup walkthrough, FAQ, automating handlers, remote management) live on the [GitHub Wiki](https://github.com/dpipstudio/botwave/wiki), mirrored into `/docs` in this repo so they're readable without a browser.

## Architecture notes

- **Protocol**: server and client speak a versioned line-based protocol defined in `shared/protocol.py` (`PROTOCOL_VERSION`). Server and client protocol versions must match on the first two components (`shared/version.py::versions_compatible`): bumping the protocol is a breaking-change-level decision.

- **Commands vs ops**: each user-facing CLI command (`start`, `stop`, `upload`, ...) has a matching file in the relevant `ops/` directory. When adding a command, add the op file and wire it into the registry, matching the pattern of existing ops.

- **Handlers**: user-defined `.hdl`/`.shdl` scripts triggered on events (`s_onready`, `l_onstart`, etc.), executed by `shared/handlers.py::HandlerExecutor`. Prefixes are load-bearing: `s_` = server, `l_` = local client. Adding a new event hook means adding both the trigger call-site and documenting it in the relevant `*.md`'s "Supported handlers" section.

- **Env vars**: read via `shared/env.py`, case-insensitive, `.env`-file-loadable, with an "immutable" marker convention. Use `Env.get(...)`, don't read `os.environ` directly in new code.

- **Config surface**: any given install can be `client`, `server` or `both`: don't both assume server and client code paths are both present on a given machine. The `client` install contains both `bw-client` and `bw-local`.

## Making changes

- Follow existing code style in the file you're editing; this repo doesn't enforce a formatter/linter, so match neighboring code rather than introducing a new style.
- Keep dependencies minimal: avoid adding new third-party packages unless there's no reasonable way around it.
- If you touch a component's CLI flags or commands, update the matching `*.md` file in the same PR. These are the canonical docs and are out of sync if left behind.
- If you touch handler event hooks, update the "Supported handlers" list in the relevant `*.md`.
- Installer/updater changes (`scripts/`, `bin/`) are higher-risk: they run as root on real hardware. Be conservative and explicit about what changed.

## Testing

There is no automated test suite in this repo. Verify changes manually (e.g. running the relevant component locally, or on real/emulated Raspberry Pi hardware for GPIO-dependent paths) before considering a change done. Don't claim something is tested unless it was actually run.

By default, [`bw_custom`](https://github.com/dpipstudio/bw_custom) is used as the backend that actually handles the FM broadcasting. If no Raspberry Pi or equivalent is available, prefer using other backends such as [`bw_jack`](https://github.com/douxxtech/bw_jack) or a custom-made test backend that follows the `shared/bw_custom.py` requirements.

## Commit conventions

Follow `CONTRIBUTING.md`: no vague commit messages, mention the affected component (e.g. `server: fix client desync on start`).

## Safety context

BotWave transmits real FM radio signals. This is subject to local broadcasting regulations in most jurisdictions. Keep this in mind if asked to change default frequencies, power-related behavior, or remove the warnings present in the wiki/installer. Don't strip those without being asked to.