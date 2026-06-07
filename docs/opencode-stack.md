# OpenCode stack

OpenCode AI CLI as a Docker Compose service. Runs from any directory by mounting the host's current directory as `/workspace`.

## Quick start

```
./launch-opencode.sh
```

This calls `docker compose --profile tools run --rm --name "opencode-$(basename $PWD)" opencode`.

## How it works

| Mechanism | Detail |
|-----------|--------|
| **Workspace** | `${PWD}:/workspace` — mounts whatever directory you run from into the container |
| **User** | Runs as non-root `opencode` user inside the container |
| **State** | Persistent named volumes survive container `--rm` removal |
| **Container name** | Set at runtime via `--name opencode-<dirname>`, allowing simultaneous instances |

## Persistent volumes

| Volume | Container path | Stores |
|--------|---------------|--------|
| `opencode_config` | `/home/opencode/.config/opencode` | `opencode.json`, agents, plugins |
| `opencode_data` | `/home/opencode/.local/share/opencode` | `auth.json` (provider tokens) |
| `opencode_state` | `/home/opencode/.local/state/opencode` | Session state |
| `opencode_cache` | `/home/opencode/.cache/opencode` | Temporary caches |

Volumes are named `{project}_opencode_*` where the project name defaults to the compose file's parent directory. They persist across restarts and are only removed with `docker compose down -v`.

## Running from any directory

Because the compose file uses `${PWD}` for the workspace mount, you can launch opencode on any project:

```bash
# Work on project A
cd ~/projects/app-a
/path/to/code-inference-ai/launch-opencode.sh

# In another terminal, work on project B
cd ~/projects/app-b
/path/to/code-inference-ai/launch-opencode.sh
```

Each instance gets a unique container name (`opencode-app-a`, `opencode-app-b`) so they run simultaneously without collision. Volumes are shared under the same compose project — `auth.json` is common across all instances.

## Running with full isolation (`--full-isolation`)

Pass `--full-isolation` to give each workspace its own set of persistent volumes:

```bash
cd ~/projects/app-a
/path/to/code-inference-ai/launch-opencode.sh --full-isolation

cd ~/projects/app-b
/path/to/code-inference-ai/launch-opencode.sh --full-isolation
```

This adds `-p <dirname>` to the compose command, scoping all volumes to that project. Each workspace gets dedicated config, auth, cache, and state — nothing leaks between projects.

**Tradeoff:** You must authenticate provider tokens separately in each isolated workspace (`opencode auth login`).

## Volume scope comparison

| | Without `--full-isolation` | With `--full-isolation` |
|---|---|---|
| Container name | `opencode-<dirname>` | `opencode-<dirname>` |
| Volume prefix | `code-inference-ai_*` (repo name) | `<dirname>_*` (workspace name) |
| Auth tokens | Shared | Per-workspace |
| Config | Shared | Per-workspace |
| Cache | Shared | Per-workspace |

## Manual invocation (without the script)

```bash
# Default (shared volumes)
docker compose --profile tools run --rm --name "opencode-$(basename $PWD)" opencode

# Full isolation
docker compose -p "$(basename $PWD)" --profile tools run --rm --name "opencode-$(basename $PWD)" opencode
```

## Running on a different project without this compose file

If the project doesn't have `code-inference-ai`'s compose file available, fall back to raw Docker:

```bash
docker run -it --rm -v $(pwd):/workspace ghcr.io/anomalyco/opencode
```

(Without persistent volumes — state is lost on exit.)

## Troubleshooting

- **"container name already exists"** — Another opencode instance is still running. Either exit it, or instances are in different directories and `--name` collision occurred. Use `--full-isolation` or remove stale containers with `docker rm opencode-<name>`.
- **Permission denied writing to workspace** — The bind-mounted `${PWD}` directory is owned by the host user, but the container runs as `opencode`. OpenCode can read/write files in `/workspace` as the `opencode` user. If your host directory has restrictive permissions, chmod it or run with `user: root`.
