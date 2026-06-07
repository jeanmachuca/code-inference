# Project settings reference

## `pyproject.toml` — Project metadata, ruff, pytest

**`[project]`**
| Setting | Value |
|---------|-------|
| `name` | `code-inference-ai` |
| `version` | `0.1.0` |
| `requires-python` | `>=3.12` |

**`[tool.ruff]`**
| Setting | Value |
|---------|-------|
| `target-version` | `py312` |
| `line-length` | `100` |

**`[tool.ruff.lint]`**
| Setting | Value |
|---------|-------|
| `select` | `E, F, I, N, W, UP, SIM` |

**`[tool.ruff.format]`**
| Setting | Value |
|---------|-------|
| `quote-style` | `single` |

**`[tool.pytest.ini_options]`**
| Setting | Value |
|---------|-------|
| `pythonpath` | `["src/services/api"]` |
| `testpaths` | `["tests"]` |

Dual with `pytest.ini` (root) — identical content. Kept for tools that only read `pyproject.toml`.

---

## `pytest.ini` (root) — Pytest config (CI + host runs)

| Setting | Value |
|---------|-------|
| `pythonpath` | `src/services/api` |
| `testpaths` | `tests` |

Makes `app.*` importable from `src/services/api`. Used by CI and when running pytest outside Docker.

---

## `src/services/api/pytest.ini` — Pytest config (in-container)

| Setting | Value |
|---------|-------|
| `pythonpath` | `.` |
| `testpaths` | `tests` |

Used inside the `api` container where the working directory is `/app` and `./app/` is the Python package. Overrides the root config.

---

## `dev-requirements.txt` — Dev tooling (not in production)

```
pre-commit==4.1.0
ruff==0.9.6
mypy==1.15.0
```

Installed by CI lint job and by developers for local pre-commit hooks.

---

## `src/services/api/requirements.txt` — API runtime dependencies

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic-settings==2.7.0
slowapi==0.1.9
pytest==8.3.4
```

NOTE: `pytest` is a runtime dep because it's installed in the production image to support in-container test runs (`make test`). Only pinned versions, no ranges.

---

## `.pre-commit-config.yaml` — Pre-commit hooks

| Hook | Source | Notes |
|------|--------|-------|
| `trailing-whitespace` | `pre-commit-hooks` v5.0.0 | |
| `end-of-file-fixer` | `pre-commit-hooks` v5.0.0 | |
| `check-yaml` | `pre-commit-hooks` v5.0.0 | |
| `check-added-large-files` | `pre-commit-hooks` v5.0.0 | `--maxkb=500` |
| `ruff` | `ruff-pre-commit` v0.9.6 | runs with `--fix` |
| `ruff-format` | `ruff-pre-commit` v0.9.6 | |
| `mypy` | `mirrors-mypy` v1.15.0 | `--no-strict-optional --ignore-missing-imports`, additional deps: pydantic, httpx, fastapi, slowapi, pydantic-settings |

---

## `.env.example` / `.env` — Environment variables

| Variable | Default (example) | Actual (.env) | Purpose |
|----------|-------------------|---------------|---------|
| `MODEL_FILENAME` | `model.gguf` | `qwen2.5-coder-3b-instruct-q4_k_m.gguf` | GGUF file in `model_data` volume |
| `CONTEXT_SIZE` | `1024` | `16384` | llama.cpp context window |
| `MAX_TOKENS` | `256` | `256` | Max tokens for inference |
| `THREADS` | `2` | `2` | CPU threads for llama.cpp |
| `TOOLS` | (not in example) | `all` | llama.cpp tool support |
| `INFERENCE_URL` | `http://inference:8080` | `http://inference:8080` | API → inference URL |
| `RATE_LIMIT_PER_MINUTE` | `30` | `30` | Rate limit on `/v1/chat/completions` |
| `MAX_PROMPT_CHARS` | `8000` | `8000` | Char-level truncation threshold |
| `API_PORT` | `8000` | (not set, uses default) | Host port for API |

`.env` is gitignored; copy from `.env.example`.

---

## `.dockerignore` — Docker build context exclusion

```
__pycache__
.pytest_cache
*.pyc
.git
docs
```

NOTABLE: `docs/` is excluded — you cannot COPY docs into any Docker image. If you need docs available at runtime, restructure or serve externally.

---

## `.gitignore` — Git exclusion

```
.env
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.egg-info/
dist/
build/
*.gguf
*.bin
docs/models/*.gguf
!docs/models/README.md
models/*
!models/README.md
opencode.json
```

NOTABLE: `opencode.json` is gitignored (local OpenCode config). `models/*` and `*.gguf` are excluded (large weights). But `docs/models/README.md` and `models/README.md` are force-included.

---

## `docker-compose.yml` — Service orchestration

**Build context:** `.` (project root) for all services.

**Services:**

| Service | Container name | Profiles | Build/Image |
|---------|---------------|----------|-------------|
| `inference-vllm` | `inference-vllm` | `alternate-inference` | Builds `src/inference-vllm/Dockerfile` |
| `inference` | `llama-inference` | `stack`, `inference` | `ghcr.io/ggml-org/llama.cpp:server-cuda12-b9538` |
| `api` | `llama-api` | `stack` | Builds `src/services/api/Dockerfile` |
| `opencode` | `opencode` | `tools` | Builds `src/opencode-stack/Dockerfile` — mounts `${PWD}:/workspace` |

**Networks:** `internal` (bridge) — shared between `inference` and `api`.

**Volumes:**
| Volume | Driver | Source | Mount |
|--------|--------|--------|-------|
| `model_data` | local bind | `./models` | `/models:ro` on inference |
| `training_data` | local (auto) | named volume | `/training:rw` on api |

**inference container** defaults from environment:
| Flag | Value |
|------|-------|
| `-m` | `/models/${MODEL_FILENAME:-model.gguf}` |
| `--host` | `0.0.0.0` |
| `--port` | `8080` |
| `--ctx-size` | `${CONTEXT_SIZE:-16384}` |
| `--threads` | `${THREADS:-6}` |
| `--jinja` | enabled |
| `--tools` | `${TOOLS:-all}` |

NOTE: The default `CONTEXT_SIZE` in `docker-compose.yml` is `16384` (different from `.env.example`'s `1024`). The `.env` sets it to `16384` and `.env.example` has `1024`.

**api container** environment:
| Variable | Default |
|----------|---------|
| `INFERENCE_URL` | `http://inference:8080` |
| `RATE_LIMIT_PER_MINUTE` | `30` |
| `MAX_PROMPT_CHARS` | `8000` |

---

## `src/services/api/Dockerfile` — API image

| Setting | Value |
|---------|-------|
| Base | `python:3.12-alpine3.21` |
| Workdir | `/app` |
| System deps | `ca-certificates` |
| CMD | `uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| Port | `8000` |

Two-phase COPY: first `requirements.txt` + `pytest.ini` for layer caching, then `app/` and `tests/`.

---

## `src/inference-vllm/Dockerfile` — vLLM alternative

| Setting | Value |
|---------|-------|
| Base | `ubuntu:latest` |
| System deps | `python3, python3-pip, curl` |
| CMD | `vllm serve Qwen/Qwen3-Coder-Next` |
| Volume | `/models` |

Unpinned base image (`ubuntu:latest`).

---

## `src/llama-stack/Dockerfile` — Meta CLI for weight downloads

| Setting | Value |
|---------|-------|
| Base | `python:3` |
| Pip | `llama-stack llama-models` |
| CMD | `llama-model --help` |
| Volume | `/models` |

Entrypoint is empty (`ENTRYPOINT []`) so arbitrary commands can be passed.

---

## `src/ollama-stack/Dockerfile` — Ollama CLI

| Setting | Value |
|---------|-------|
| Base | `ubuntu` |
| System deps | `curl, zstd` |
| Install | curl-piped `ollama.com/install.sh` |
| CMD | `ollama --help` |
| Volume | `/models` |

Unpinned base image (`ubuntu`). Installs via shell pipe — security note for production.

---

## `src/opencode-stack/Dockerfile` — OpenCode CLI

| Setting | Value |
|---------|-------|
| Base | `ghcr.io/anomalyco/opencode` |
| Workdir | `/workspace` |

Minimal — just re-tags the published opencode image and sets WORKDIR to `/workspace`. The compose service mounts `${PWD}:/workspace` so the container always sees the host directory you run from. Uses `stdin_open: true` and `tty: true` for interactive sessions.

Usage:
```
# From this repo (uses launch-opencode.sh wrapper):
./launch-opencode.sh

# From any directory with this compose file available:
docker compose --profile tools run --rm opencode
```

---

## `.github/workflows/ci.yml` — CI pipeline

| Setting | Value |
|---------|-------|
| Triggers | Push/PR to `main`, `development` |
| Python | `3.12` |
| Runner | `ubuntu-latest` |

**lint job:** Installs `src/services/api/requirements.txt` + `dev-requirements.txt`. Runs `ruff check`, `ruff format --check .`, `mypy src/`.

**test job:** Installs only `src/services/api/requirements.txt`. Runs `pytest -v`.

---

## `Makefile` — Convenience aliases

| Target | Command | Profiles |
|--------|---------|----------|
| `build` | `docker compose build --profile stack --profile tools` | stack, tools |
| `test` | `docker compose --profile stack run --rm --no-deps api pytest -v` | stack |
| `up` | `docker compose --profile stack up --build` | stack |

NOTE: `make build` now also builds the `opencode` service (tools profile), which pulls/updates the `ghcr.io/anomalyco/opencode` image.

---

## `opencode.json` / `opencode.json.example` — OpenCode (AI agent) config

The actual `opencode.json` is gitignored (local override). `opencode.json.example` is committed as a template.

**Actual (`opencode.json`):**
```
provider: code-inference (npm @ai-sdk/openai-compatible)
model:    qwen2.5-coder-3b-instruct-q4_k_m.gguf
  name:           Qwen 2.5 Coder 3B
  supportsToolCalls: true
  context limit:  65536
  output limit:   32768
baseURL:  http://localhost:8080/v1
instructions: [AGENTS.md, .opencode/instructions/git-workflow.md]
```

**Example (`opencode.json.example`):**
```
provider: code-inference (npm @ai-sdk/openai-compatible)
model:    model.gguf
  name:           Meta Llama 3 1B Instruct
  contextWindow:  4096
baseURL:  http://localhost:8080/v1
```

---

## `AGENTS.md` — AI agent workspace instructions

Loaded by `opencode.json` as agent instructions. Contains commands, architecture, code style, setup, testing quirks, CI info, and gotchas.

---

## `.opencode/instructions/git-workflow.md` — AI agent git rules

Loaded by `opencode.json` as an agent instruction. Always applied. Enforces:
- Topic branches from `development`, PR to `development`, release to `main`
- No rebase
- Keep merged branches
- Annotated SemVer tags
- Sync-git workflow
