#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Prompt to create default config files if missing (skip for --help)
case "${1:-}" in
  --help|-h) ;;
  *)
    MISSING=""
    if [ ! -f "./opencode.json" ]; then
      MISSING="$MISSING  - opencode.json\n"
    fi
    if [ ! -f "./AGENTS.md" ]; then
      MISSING="$MISSING  - AGENTS.md\n"
    fi
    if [ ! -f "./.opencode/instructions/git-workflow.md" ]; then
      MISSING="$MISSING  - .opencode/instructions/git-workflow.md\n"
    fi
    if [ -n "$MISSING" ]; then
      echo "Missing config files in $(pwd):"
      printf "$MISSING"
      printf "Create from templates? [Y/n]: "
      read -r REPLY || true
      case "$REPLY" in
        n|N|no|No) echo "Skipping." ;;
        *)
          if [ ! -f "./opencode.json" ]; then
            cp "$SCRIPT_DIR/opencode.json.example" "./opencode.json"
            echo "Created $(pwd)/opencode.json"
          fi
          if [ ! -f "./AGENTS.md" ]; then
            cp "$SCRIPT_DIR/AGENTS.md" "./AGENTS.md"
            echo "Created $(pwd)/AGENTS.md"
          fi
          if [ ! -f "./.opencode/instructions/git-workflow.md" ]; then
            mkdir -p "./.opencode/instructions"
            cp "$SCRIPT_DIR/.opencode/instructions/git-workflow.md" "./.opencode/instructions/git-workflow.md"
            echo "Created $(pwd)/.opencode/instructions/git-workflow.md"
          fi
          echo "Customize as needed."
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
