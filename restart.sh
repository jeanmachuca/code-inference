# 1. Stop your containers and remove the old volume reference
docker compose --profile stack down -v

# 2. Double check your local models folder has the downloaded file
ls -lh ./models/

# 3. Boot the stack back up with clean volume initializations
docker compose --profile stack up --force-recreate --build --remove-orphans -d