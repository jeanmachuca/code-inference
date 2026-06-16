# syntax=docker/dockerfile:1
# Wrapper over ghcr.io/ggml-org/llama.cpp:server with Python + llama-stack
# for cases where we need additional tooling on top of the base inference image.
#
# Models are loaded at runtime from the model_data bind mount (/models),
# same as the stock inference service.
#
# Examples (from repo root):
#   docker compose --profile stack build llama-stack
#   docker compose --profile stack run --rm llama-stack llama-model list
#   docker compose --profile stack run --rm -it llama-stack llama-model download --source meta --model-id <MODEL_ID>

FROM ghcr.io/ggml-org/llama.cpp:server

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir llama-stack llama-models

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /models
VOLUME ["/models"]

ENTRYPOINT []
CMD ["llama-model", "--help"]
