# code-inference-ai

Local/on-premise code inference stack with sovereign data governance. FastAPI gateway proxies to local llama.cpp server; all inference stays on hardware you control. PII stripping, char-level truncation, intent tagging. No prompts leave the host.

## Commands (from repo root)

| Action | Command |
|--------|---------|
| Build all images | `make build` |
| Run full stack | `make up` |
| Run unit tests | `make test` |
| Run a single test | `docker compose --profile stack run --rm --no-deps api pytest -v tests/api/test_prompt.py::test_rut_masked_in_user_message` |
| Shell into API container | `docker compose --profile stack run --rm api sh` |
| Restart stack (destroys volumes) | `./restart.sh` |
| Install pre-commit hooks (once) | `pip install -r dev-requirements.txt && pre-commit install` |
| Run all pre-commit hooks on all files | `pre-commit run --all-files` |
| Ruff lint | `ruff check .` |
| Ruff format check | `ruff format --check .` |
| mypy | `mypy src/` |
| Launch opencode (from any dir) | `./launch-opencode.sh` |
| Launch opencode (isolated state) | `./launch-opencode.sh --full-isolation` |

## Architecture

- **`src/services/api/app/main.py`** — FastAPI entrypoint. `GET /health`, `GET /health/ready` (probes inference `/v1/models`), `POST /v1/chat/completions` (proxies to inference after prompt processing).
- **`src/services/api/app/prompt.py`** — Prompt preprocessing: Chilean RUT masking via regex, char-level truncation (last user message only), intent tagging from `X-code_inference-Intent` header.
- **`src/services/api/app/config.py`** — pydantic-settings loaded from `.env` at module level.
- **`docker-compose.yml`** — project root is Compose build context. Profiles: `stack` (default, inference+api), `tools` (llama-stack CLI), `alternate-inference` (vLLM).
- **`src/inference-vllm/`, `src/llama-stack/`, `src/ollama-stack/`, `src/opencode-stack/`** — alternative backends and CLI tools (not in default `stack` profile).
- **Compose volumes:** `model_data` (bind-mounts `./models/`, read-only for inference), `training_data` (writable for API).
- **`opencode.json`** loads instructions from this file and `.opencode/instructions/git-workflow.md`. Local config; gitignored.

## Code style

- Ruff: line-length 100, target py312, lint select `E,F,I,N,W,UP,SIM`, **single quotes** (`ruff format --check .`).
- mypy: runs with `--no-strict-optional --ignore-missing-imports`.
- pre-commit: trailing-whitespace, end-of-file-fixer, ruff (`--fix`), ruff-format, mypy.
- No raw prompts logged — only `request_id`, `tags`, `truncated`, `pii_masked` flags (privacy requirement).
- Response headers: `X-Request-Id`, `X-Prompt-Truncated`, `X-Prompt-Pii-Masked`.

## Setup

1. `cp .env.example .env`, adjust vars (MODEL_FILENAME, CONTEXT_SIZE, INFERENCE_URL, RATE_LIMIT_PER_MINUTE, MAX_PROMPT_CHARS).
2. Place a GGUF model in `./models/` (see `docs/models/README.md`).
3. `make build && make up`.

## Testing

- **Unit tests only** (no integration tests, no inference needed).
- Single test file: `tests/api/test_prompt.py` (3 tests: RUT masking, intent tagging, truncation).
- **Dual pytest configs:** root `pyproject.toml`/`pytest.ini` set `pythonpath=src/services/api` for CI/local runs; container has `src/services/api/pytest.ini` with `pythonpath=.`. New test files go in `tests/api/`.
- Runtime deps (incl. pytest) in `src/services/api/requirements.txt`; dev tools in `dev-requirements.txt`.
- To add tests: mirror `tests/api/test_*.py` pattern; new runtime deps in `src/services/api/requirements.txt`.

## CI (`.github/workflows/ci.yml`)

- Triggers: push/PR to `main` or `development`.
- **lint job:** installs runtime + dev deps, runs ruff check, ruff format check, mypy.
- **test job:** installs only runtime deps, runs `pytest -v`.

## Important gotchas

- **`opencode.json` is gitignored** — not committed.
- **`.dockerignore` excludes `docs/`** — cannot COPY docs into image.
- **`restart.sh`** runs `docker compose down -v` which **destroys volumes** (model_data bind-mount survives, training_data is wiped).
- **Default branch:** `development`. Gitflow + SemVer. See `.opencode/instructions/git-workflow.md`. No rebase. Keep merged topic branches.
- **`models/*` gitignored** (except `docs/models/README.md`). Do not commit GGUF files.
