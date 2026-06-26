#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORIG_PWD="$PWD"

NAME_SUFFIX="$(basename "$ORIG_PWD" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

cd "$SCRIPT_DIR"

if [ "$1" = "--full-isolation" ]; then
  shift
  PWD="$ORIG_PWD" exec docker compose -f docker-compose-notools.yml -p "$NAME_SUFFIX" --profile stack run --rm --name "opencode-$NAME_SUFFIX" --build --remove-orphans opencode "$@"
else
  PWD="$ORIG_PWD" exec docker compose -f docker-compose-notools.yml --profile stack run --rm --name "opencode-$NAME_SUFFIX" --build --remove-orphans opencode "$@"
fi
