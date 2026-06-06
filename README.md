# code-inference-ai

AI assistant component for code-inference. **Documentation:** **[docs/](docs/)** (requirements, **[architecture](docs/architecture.md)**, **[rate limits](docs/rate-limits.md)**, plan). **Implementation:** **[src/](src/)** (API service); **tests:** **[tests/](tests/)**. Compose build context is the **project root** (see `docker-compose.yml`). **Default branch:** `development`. Branching and releases: **[docs/git-workflow.md](docs/git-workflow.md)** (Gitflow, SemVer, tags `vMAJOR.MINOR.PATCH`).

## Stack (development)

- **Docker Compose** — `api` (FastAPI gateway + prompt management) and `inference` (`ghcr.io/ggml-org/llama.cpp:server`).
- **Compose profiles** — **`stack`**: `inference` + `api`; **`tools`**: `llama-stack` (Meta **`llama-model`** CLI). Use `docker compose --profile stack up` (see [docs/models/README.md](docs/models/README.md)).
- **Volumes** — `model_data` (GGUF weights), `training_data` (for future training jobs).

## Prerequisites

- Docker with Compose v2

## Quick start

1. Copy **`.env.example`** to **`.env`** and adjust if needed.
2. Obtain a **GGUF** checkpoint (see **[docs/models/README.md](docs/models/README.md)** for where to download, how to verify the file, and how to copy it into the `model_data` volume as **`model.gguf`** or set **`MODEL_FILENAME`**).
3. **Build** and **run**:

   ```bash
   make build
   docker compose --profile stack up
   ```

4. **API** (after inference is healthy): `http://localhost:8000`  
   - `GET /health` — liveness  
   - `GET /health/ready` — checks inference `/v1/models`  
   - `POST /v1/chat/completions` — OpenAI-compatible proxy (after [prompt preprocessing](src/services/api/app/prompt.py))

## Tests (no GPU / no model required for unit tests)

```bash
make test
```

Runs `pytest` inside the `api` container (`--no-deps` so inference is not required).

## Documentation

| Path | Description |
|------|-------------|
| [docs/](docs/) | Requirements, architecture, ADRs, regulations |
| [docs/models/](docs/models/README.md) | GGUF weights: sourcing, verification, Docker `model_data` volume |
| [src/](src/) | API service |
| [tests/](tests/) | Pytest suite (run via `make test` in Docker) |
# code-inference
