# code-inference

OpenCode AI CLI launcher — runs opencode in your project with a preconfigured local inference stack.

## Quick start

```bash
docker pull ghcr.io/jeanmachuca/code-inference

# Run opencode in your current project (compose mode — needs repo clone)
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd):$(pwd)" \
  -w "$(pwd)" \
  ghcr.io/jeanmachuca/code-inference

# Run with isolated state (works from any directory)
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd):$(pwd)" \
  -w "$(pwd)" \
  ghcr.io/jeanmachuca/code-inference --fresh
```

## How it works

The image contains the full [code-inference-ai](https://github.com/jeanmachuca/code-inference) repo at `/repo` with Docker CLI and Compose installed. Published to `ghcr.io/jeanmachuca/code-inference`. The entrypoint `start.sh` delegates to one of two launchers:

| Flag | Launcher | Mechanism | State |
|------|----------|-----------|-------|
| *(none)* | `launch-opencode.sh` | `docker compose --profile tools run --rm opencode` | Ephemeral (no volumes) |
| `--fresh` | `launch-fresh-opencode.sh` | `docker run ... ghcr.io/anomalyco/opencode` with named volumes | Persistent across runs |

The launchers build and run the opencode container with the repo's compose file, mounting your project directory as the workspace. The local inference backend (`llama.cpp`, API, prompt processing) runs alongside via `docker compose --profile stack up` if needed.

> **Docker socket (DooD, not DinD):** The image binds the host's Docker socket (`/var/run/docker.sock`), so `docker` and `docker compose` commands inside the container are executed by the **host's** Docker daemon. This is Docker-outside-of-Docker (socket binding), not Docker-in-Docker (which would require `--privileged` and running a nested `dockerd`). The launch scripts talk to the host daemon directly — no nested runtime needed.

## Requirements

- Docker with Compose v2
- Docker socket mounted (`-v /var/run/docker.sock:/var/run/docker.sock`)
- Your project directory mounted at the same path (`-v "$(pwd):$(pwd)" -w "$(pwd)"`)

## Development

See [AGENTS.md](AGENTS.md) for dev commands and repo architecture.

### Stack services

| Service | Container | Profile | Image |
|---------|-----------|---------|-------|
| `inference` | `llama-inference` | `stack` | `ghcr.io/ggml-org/llama.cpp:server-cuda12-b9538` |
| `api` | `llama-api` | `stack` | `src/services/api/Dockerfile` |
| `opencode` | `opencode` | `tools` | `src/opencode-stack/Dockerfile` |

### Quick start (development)

```bash
cp .env.example .env
# Place a GGUF in ./models/
make build && make up
```

### Tests

```bash
make test
```
