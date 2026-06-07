# syntax=docker/dockerfile:1
# OpenCode CLI — AI coding assistant in Docker.
# Designed to run on any host directory by binding the current folder to /workspace.
# The compose service uses ${PWD} so opencode works from any directory,
# not just this repo — mount any project folder into the container.
#
# Usage (from any directory with access to this compose file):
#   docker compose --profile tools run --rm opencode
#
# To run outside this repo's compose context:
#   docker run -it --rm -v $(pwd):/workspace ghcr.io/anomalyco/opencode

FROM ghcr.io/anomalyco/opencode

# Git + SSH are needed by opencode's git-aware features (push, pull)
RUN apk add --no-cache git openssh

# Dev dependencies for linting/formatting (pre-commit, ruff, mypy)
RUN pip install --no-cache-dir pre-commit==4.1.0 ruff==0.9.6 mypy==1.15.0

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
