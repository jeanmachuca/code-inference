#!/bin/sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ORIG_PWD="$PWD"

PROJECT_FLAG=""
NAME_SUFFIX="$(basename "$ORIG_PWD")"

if [ "$1" = "--full-isolation" ]; then
  PROJECT_FLAG="-p $NAME_SUFFIX"
  shift
fi

cd "$SCRIPT_DIR"
PWD="$ORIG_PWD" docker compose $PROJECT_FLAG --profile stack run --rm --name "opencode-$NAME_SUFFIX" --build --remove-orphans opencode "$@"
