# code-inference AI — convenience targets (Docker-only per project rules)

.PHONY: build test up

build:
	docker compose build --profile stack --profile tools

test:
	docker compose --profile stack run --rm --no-deps api pytest -v

up:
	docker compose --profile stack up --build
