# syntax=docker/dockerfile:1
# Toolbox image: Meta Llama Models CLI — downloads weights into the shared model_data volume.
# Requires Meta license approval and signed URL when using --source meta.
#
# Examples (from repo root, after: docker compose build --profile tools llama-stack):
#   docker compose --profile tools run --rm llama-stack llama-model list
#   docker compose --profile tools run --rm -it llama-stack llama-model download --source meta --model-id <MODEL_ID>
#
# Meta’s CLI typically writes native checkpoints, not GGUF. For llama.cpp you still need a .gguf
# on /models (convert or copy a GGUF) — see docs/models/README.md.

FROM python:3

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir llama-stack llama-models

WORKDIR /models
VOLUME ["/models"]

ENTRYPOINT []
CMD ["llama-model", "--help"]
