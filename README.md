# I2PDM2-FastAPI-Backend

A simple API server for i2pdm2 pest recognition — recognition only. There is
no LINE bot, user-profile, or history/trend feature here; every detection
request is logged as one row in the `pest_records` table (see
`I2PDM2-mysql`), with no user identity attached.

## Quick Start (Docker)

**Prerequisites:**
* Docker + Docker Compose v2
* An NVIDIA GPU with a driver new enough for CUDA 12.1+ — `nvidia-smi`
  should report "CUDA Version: 12.1" or higher
* `nvidia-container-toolkit` installed, so `docker info` lists an `nvidia`
  runtime

**Setup:**
1. Copy `.env.example` to `.env`. `DATABASE_URL` must match the account you
   set up in `I2PDM2-mysql/.env`.
2. Place the model weight files in `app/pest/model/` — these are not in git
   (delivered separately, e.g. secure file transfer). See
   [app/pest/model/README.md](app/pest/model/README.md) for the exact list.
3. Create the network shared with `I2PDM2-mysql` (once, if it doesn't
   already exist): `docker network create pest_app_network`
4. Start `I2PDM2-mysql` first — this service connects to it on startup.
5. `docker compose up -d --build`

### API Document
Local: http://localhost:28000/docs

To deploy under a real domain/reverse-proxy path, set `ROOT_PATH` in `.env` (see `.env.example`) — the docs will then be served at `https://<your-domain>/<ROOT_PATH>/docs`.

> At the time of writing, parts of the API server are experimental, and hence subject to change.

## Deployment

```bash
# Build
docker compose up -d --build
# Start (without build)
docker compose up -d
# Stop
docker compose down
# Remove volume
docker compose down --volume
# Inspect log
docker cp backend:/i2pdm2/tmp/log/app.log .
```

## Development

* Dependencies (including the pinned `torch`/`torchvision`/`torchaudio` build) are in
  [requirements.txt](requirements.txt)
* Docker, nvidia-container-toolkit (see Quick Start above)

### Format

```bash
bash ./scripts/format.sh
```
### Python linter check

```bash
bash ./scripts/lint.sh
```


