# code-inference-ai

Local inference stack. FastAPI gateway proxies to llama.cpp; all inference stays on-host. PII masking (Chilean RUT), char-level truncation, intent tagging.

Git workflow: see `.opencode/instructions/git-workflow.md` (loaded via `opencode.json` instruction).

## Docker commands

| Action | Command |
|--------|---------|
| Build stack + tools images | `make build` |
| Run stack (always rebuilds) | `make up` |
| Unit tests (no inference needed) | `make test` |
| Single test | `docker compose --profile stack run --rm --no-deps api pytest -v tests/api/test_prompt.py::TEST_NAME` |
| Shell into API container | `docker compose --profile stack run --rm api sh` |
| Full restart (destroys all named volumes: `training_data`, `opencode_*`) | `./restart.sh` |

## Host commands (for CI / pre-commit)

| Action | Command |
|--------|---------|
| Ruff lint | `ruff check .` |
| Ruff format check | `ruff format --check .` |
| mypy | `mypy --config-file=pyproject.toml --no-strict-optional --ignore-missing-imports src/` |
| Pre-commit (all hooks) | `pre-commit run --all-files` |

## Architecture

- **Entrypoint:** `src/services/api/app/main.py:22` — FastAPI app. Routes: `GET /health`, `GET /health/ready` (pings inference `/v1/models`), `POST /v1/chat/completions` (proxies after prompt processing).
- **Prompt layer:** `src/services/api/app/prompt.py` — RUT masking via regex `_RUT_RE`, char-level truncation (last user message only, appends `…[truncated]`), intent tagging from `X-code_inference-Intent` header.
- **Config:** `src/services/api/app/config.py` — pydantic-settings reads `.env` at module level (singleton).
- **Startup wait:** API polls `inference:8080/v1/models` for up to 60s before accepting requests.
- **Retry:** 3 attempts with exponential backoff on connect/timeout errors to inference.
- **Streaming:** `stream: true` returns SSE passthrough from inference; extra `model_extra` fields (tools, tool_choice, etc.) flow through.
- **Compose profiles:** `stack` (inference+api, default), `tools` (opencode CLI), `alternate-inference` (vLLM experimental, **not wired** to `internal` network). Build context is project root.
- **Volumes:** `model_data` (bind-mount `./models/:ro`), `training_data` (named, **destroyed by `restart.sh`**).
- **Stack Dockerfiles:** `src/services/api/Dockerfile` (python:3.12-alpine, uvicorn), `src/inference-vllm/`, `src/llama-stack/`, `src/ollama-stack/`, `src/opencode-stack/` (standalone builds outside default stack).
- **Inference container** starts with `--jinja --tools ${TOOLS:-all} --ctx-size ${CONTEXT_SIZE:-16384} --threads ${THREADS:-6}`. Image: `ghcr.io/ggml-org/llama.cpp:server-cuda12-b9538`.

## Code style

- Ruff: line-length 100, target py312, lint `E,F,I,N,W,UP,SIM`, **single quotes**.
- mypy: `--no-strict-optional --ignore-missing-imports`.
- No raw prompts logged — only `request_id`, `tags`, `truncated`, `pii_masked` flags.
- Response headers: `X-Request-Id`, `X-Prompt-Truncated`, `X-Prompt-Pii-Masked`.

## Setup

1. `cp .env.example .env`, adjust vars (see `docs/settings.md` for full reference).
2. Place a GGUF model in `./models/` (see `docs/models/README.md`).
3. `make build && make up`.

## Testing quirks

- **Unit tests only** (no inference container). Single file: `tests/api/test_prompt.py` (3 tests).
- **`pytest` is a runtime dep** in `src/services/api/requirements.txt` — intentional for in-container `make test`.
- **Dual pytest configs:** root `pyproject.toml`/`pytest.ini` set `pythonpath=src/services/api` (CI/host). Container `src/services/api/pytest.ini` sets `pythonpath=.` (workdir `/app`). New tests go in `tests/api/`.

## CI

- Triggers: push/PR to `main` or `development`.
- **lint job:** installs `requirements.txt` + `dev-requirements.txt`, runs `ruff check`, `ruff format --check .`, `mypy src/`.
- **test job:** installs only `requirements.txt`, runs `pytest -v`.

## Gotchas

- **`opencode.json` is gitignored** — `opencode.json.example` is the committed template. Actual config loads `AGENTS.md` + `.opencode/instructions/git-workflow.md`.
- **`.dockerignore` excludes `docs/`** — cannot COPY docs into any image.
- **`restart.sh`** runs `docker compose --profile stack down -v` then `up --force-recreate --build --remove-orphans -d` — destroys **all** named volumes (`training_data`, `opencode_*`). Bind-mount `model_data` survives.
- **`make build`** builds both `stack` and `tools` profiles (pulls `ghcr.io/anomalyco/opencode`).
- **`make up`** always runs `--build` (picks up local code changes).
- **`CONTEXT_SIZE`:** `.env.example` defaults to 1024; compose shell default is 16384; `.env` sets 16384. Verify your actual value.
- **`TOOLS` env var:** `.env.example` omits it; compose default is `all`; `.env` sets `TOOLS=all`.
- **`inference-vllm` is on `alternate-inference` profile, NOT on `internal` network — cannot reach API.**
- **Default branch:** `development`. Gitflow + SemVer. No rebase. Keep merged topic branches.
- **`models/*` and `*.gguf` gitignored** — do not commit weights.
- **README/docs cross-references that do not exist on disk:** `docs/architecture.md`, `docs/rate-limits.md`, `docs/git-workflow.md`.
