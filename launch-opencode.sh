#!/bin/sh
PROJECT_FLAG=""
NAME_SUFFIX="$(basename "$PWD")"

if [ "$1" = "--full-isolation" ]; then
  PROJECT_FLAG="-p $NAME_SUFFIX"
fi

docker compose $PROJECT_FLAG --profile tools run --rm --name "opencode-$NAME_SUFFIX" opencode
