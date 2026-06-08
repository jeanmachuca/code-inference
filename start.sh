#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Prompt to create default opencode.json if missing (skip for --help)
case "${1:-}" in
  --help|-h) ;;
  *)
    if [ ! -f "./opencode.json" ]; then
      echo "No opencode.json found in $(pwd)"
      printf "Create default config from template? [Y/n]: "
      read -r REPLY || true
      case "$REPLY" in
        n|N|no|No) echo "Skipping." ;;
        *)
          cp "$SCRIPT_DIR/opencode.json.example" "./opencode.json"
          echo "Created $(pwd)/opencode.json (customize as needed)."
          ;;
      esac
    fi
    ;;
esac

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
