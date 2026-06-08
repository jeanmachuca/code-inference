#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-}" in
  --fresh|--full-isolation)
    shift
    exec "$SCRIPT_DIR/launch-fresh-opencode.sh" "$@"
    ;;
  --help|-h)
    echo "Usage: code-inference [--fresh] [-- opencode-args]"
    echo ""
    echo "Options:"
    echo "  --fresh, --full-isolation  Run opencode standalone without the inference stack"
    ;;
  *)
    exec "$SCRIPT_DIR/launch-opencode.sh" "$@"
    ;;
esac
