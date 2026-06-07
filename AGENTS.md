# code-inference-ai

Local/on-premise inference stack. FastAPI gateway proxies to llama.cpp; all inference stays on-host. PII masking (Chilean RUT), char-level truncation, intent tagging.

## Commands

| Action | Command |
|--------|---------|
| Build all images | `make build` |
| Run full stack | `make up` |
| Run unit tests | `make test` |
| Single test | `docker compose --profile stack run --rm --no-deps api pytest -v tests/api/test_prompt.py::TEST_NAME` |
| Shell into API container | `docker compose --profile stack run --rm api sh` |
| Restart stack (destroys volumes) | `./restart.sh` |
| Ruff lint | `ruff check .` |
| Ruff format check | `ruff format --check .` |
| mypy | `mypy src/` |
| Launch opencode | `./launch-opencode.sh` |

## Architecture

- **Entrypoint:** `src/services/api/app/main.py` — FastAPI app. `GET /health`, `GET /health/ready` (pings inference `/v1/models`), `POST /v1/chat/completions` (proxies to inference after prompt processing).
- **Prompt layer:** `src/services/api/app/prompt.py` — RUT masking via regex, char-level truncation (last user message only), intent tagging from `X-code_inference-Intent` header.
- **Config:** `src/services/api/app/config.py` — pydantic-settings reads `.env` at module level.
- **Compose profiles:** `stack` (inference+api, default), `tools` (opencode CLI), `alternate-inference` (vLLM). Build context is project root.
- **Volumes:** `model_data` (bind-mount `./models/:ro`), `training_data` (named, **destroyed by `restart.sh`**).
- **`src/inference-vllm/`, `src/llama-stack/`, `src/ollama-stack/`, `src/opencode-stack/`** are standalone Docker builds, not in default stack.

## Code style

- Ruff: line-length 100, target py312, lint select `E,F,I,N,W,UP,SIM`, **single quotes**.
- mypy: `--no-strict-optional --ignore-missing-imports`, extra deps in `.pre-commit-config.yaml` (pydantic, httpx, fastapi, slowapi, pydantic-settings).
- No raw prompts logged — only `request_id`, `tags`, `truncated`, `pii_masked` flags.
- Response headers: `X-Request-Id`, `X-Prompt-Truncated`, `X-Prompt-Pii-Masked`.

## Setup

1. `cp .env.example .env`, adjust vars (`MODEL_FILENAME`, `CONTEXT_SIZE`, `INFERENCE_URL`, `RATE_LIMIT_PER_MINUTE`, `MAX_PROMPT_CHARS`).
2. Place a GGUF model in `./models/`.
3. `make build && make up`.

## Testing quirks

- **Unit tests only** (no inference container needed). Single file: `tests/api/test_prompt.py` (3 tests).
- **`pytest` is a runtime dep** in `src/services/api/requirements.txt` — intentional for in-container `make test`.
- **Dual pytest configs:** root `pyproject.toml`/`pytest.ini` set `pythonpath=src/services/api` (CI/host). Container `src/services/api/pytest.ini` sets `pythonpath=.` (workdir `/app`). New tests go in `tests/api/`.

## CI (`.github/workflows/ci.yml`)

- Triggers: push/PR to `main` or `development`.
- **lint job:** installs runtime + dev deps, runs `ruff check`, `ruff format --check .`, `mypy src/`.
- **test job:** installs only runtime deps, runs `pytest -v`.

## Gotchas

- **`opencode.json` is gitignored** — `opencode.json.example` is the committed template.
- **`.dockerignore` excludes `docs/`** — cannot COPY docs into any image.
- **`restart.sh`** runs `docker compose --profile stack down -v` — destroys named `training_data` volume (bind-mount `model_data` survives).
- **`make build`** builds both `stack` and `tools` profiles (pulls `ghcr.io/anomalyco/opencode`).
- **`CONTEXT_SIZE` env:** `.env.example` defaults to 1024, but `docker-compose.yml` default is 16384 (actual `.env` uses 16384).
- **Default branch:** `development`. Gitflow + SemVer. No rebase. Keep merged topic branches. Active git rules: `.opencode/instructions/git-workflow.md`.
- **`models/*` and `*.gguf` gitignored** — do not commit weights.
- **Full project config reference:** `docs/settings.md` documents every file, env var, and workflow in detail.
