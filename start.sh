#!/bin/sh
set -e

case "${1:-}" in
  --fresh|--full-isolation)
    shift
    exec /repo/launch-fresh-opencode.sh "$@"
    ;;
  --help|-h)
    echo "Usage: docker run [OPTIONS] code-inference [--fresh] [-- opencode-args]"
    echo ""
    echo "Options:"
    echo "  --fresh, --full-isolation  Run with fresh/isolated state per project"
    echo ""
    echo "Requires: -v /var/run/docker.sock:/var/run/docker.sock"
    echo "         -v \"\$(pwd):\$(pwd)\" -w \"\$(pwd)\""
    ;;
  *)
    exec /repo/launch-opencode.sh "$@"
    ;;
esac
