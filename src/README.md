# Source

Runnable application assets, **parallel to [`docs/`](../docs/)** and **[`tests/`](../tests/)**.

| Path | Description |
|------|-------------|
| [`services/api/`](services/api/) | FastAPI gateway, prompt management, Dockerfile |
| [`docs/models/README.md`](../docs/models/README.md) | How to load **GGUF** weights into the `model_data` Docker volume |

The repository **`docker-compose.yml`** lives at the **project root** with **profiles** **`stack`** (inference + API) and **`tools`** (`llama-stack` CLI). Build the API from **`src/services/api/Dockerfile`** with context **`.`** (project root).
