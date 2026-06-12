# syntax=docker/dockerfile:1
# OpenCode runtime — adds dev tooling on top of ghcr.io/anomalyco/opencode.
#
# Published to ghcr.io/jeanmachuca/code-inference for pre-built use.
# The compose service builds from this Dockerfile; the pre-built image
# is used via `docker run ghcr.io/jeanmachuca/code-inference` or in CI.
#
# For the recommended CLI workflow, see README.md and docs/installation.md.

FROM ghcr.io/anomalyco/opencode

# Git + SSH are needed by opencode's git-aware features (push, pull)
# Dev dependencies for linting/formatting (pre-commit, ruff, mypy)
RUN apk --update --no-cache add \
    git \
    openssh \
    python3 \
    py3-pip \
    pre-commit \
    ruff \
    nodejs \
    npm \
    deno \
    github-cli

# Create non-root user for running opencode
RUN addgroup -S opencode && adduser -S -h /home/opencode -G opencode opencode

# Create XDG directories that volumes will mount over (ensures correct
# ownership even when volumes are empty on first run)
RUN mkdir -p \
    /home/opencode/.config/opencode \
    /home/opencode/.local/share/opencode \
    /home/opencode/.local/state/opencode \
    /home/opencode/.cache/opencode \
    && chown -R opencode:opencode /home/opencode

# Override WORKDIR so the container always opens at the mounted source
WORKDIR /workspace
