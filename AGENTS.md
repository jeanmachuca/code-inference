# code-inference-ai — AGENTS.md

## Commands (run from repo root `/workspace`)

| Action | Command |
|--------|---------|
| Build all images | `make build` |
| Run full stack | `make up` or `docker compose --profile stack up` |
| Run unit tests (no GPU/model needed) | `make test` (runs `pytest` inside `api` container with `--no-deps`) |
| Run a single test | `docker compose --profile stack run --rm --no-deps api pytest -v tests/api/test_prompt.py::test_rut_masked_in_user_message` |
| Shell into API container | `docker compose --profile stack run --rm api sh` |
| Restart stack (clean volumes) | `./restart.sh` |
| Install pre-commit hooks (once) | `pip install -r dev-requirements.txt && pre-commit install` |
| Run all pre-commit hooks on all files | `pre-commit run --all-files` |
| Run ruff lint | `ruff check .` |
| Run ruff format check | `ruff format --check .` |
| Run mypy | `mypy src/` |
| CI pipeline | `.github/workflows/ci.yml` — triggered on push/PR to `main` or `development` |

## Architecture

- **`src/services/api/app/main.py`** — FastAPI entrypoint. Exposes `GET /health`, `GET /health/ready`, `POST /v1/chat/completions` (proxies to inference).
- **`src/services/api/app/prompt.py`** — Prompt preprocessing: PII masking (Chilean RUT), char-level truncation (last user message), intent tagging from `X-code_inference-Intent` header.
- **`src/services/api/app/config.py`** — pydantic-settings loaded from `.env`.
- **`src/services/api/Dockerfile`** — multi-stage? No, simple alpine build; copies `app/` and `tests/` into image.
- **`docker-compose.yml`** — Two default profiles: `stack` (inference + api) and `tools` (llama-stack CLI). Third profile `alternate-inference` for vLLM variant.
- **Linting/formatting:** ruff (`pyproject.toml` config). **Type checking:** mypy. **Orchestration:** pre-commit (`.pre-commit-config.yaml`).
- **Dev dependencies** in `dev-requirements.txt` (not used in production Docker image).
- **CI:** `.github/workflows/ci.yml` — `lint` job (ruff + mypy) and `test` job (pytest). Runs on push/PR to `main` and `development`.
- **Default branch:** `development`. Gitflow + SemVer (`vMAJOR.MINOR.PATCH`).

## Setup

1. `cp .env.example .env` and adjust.
2. Place a GGUF model in `./models/` (bind-mounted as Docker `model_data` volume). See `docs/models/README.md` for downloads.
3. `make build && make up`.

## Testing quirks

- Unit tests only (no integration tests). `pytest.ini` at root sets `pythonpath = src/services/api` — run tests from repo root.
- No inference service needed for tests (Docker `--no-deps`).
- Only test file: `tests/api/test_prompt.py` (3 tests for PII masking, intent tagging, truncation).
- To add tests, mirror `tests/api/test_*.py` pattern; new deps go in `src/services/api/requirements.txt`.

## Important gotchas

- **`opencode.json` is gitignored** — local OpenCode config, not committed.
- **`pyproject.toml`** at root — project metadata, ruff config, pytest config. **`src/services/api/requirements.txt`** for runtime deps (pinned). **`dev-requirements.txt`** for dev tools.
- **No raw prompts logged** — only `request_id`, `tags`, `truncated`, `pii_masked` flags (privacy requirement).
- **Response headers:** `X-Request-Id`, `X-Prompt-Truncated`, `X-Prompt-Pii-Masked`.
- **Request header:** `X-code_inference-Intent` sets the intent tag.
- **vLLM profile** (`alternate-inference`) uses GPU reservation; the default inference service (`ghcr.io/ggml-org/llama.cpp:server-cuda12-b9538`) also supports GPU.
- `.env` must exist before `docker compose up` — copied from `.env.example`.
