# I2PDM2-FastAPI-Backend

A simple API server for i2pdm2 backend.


### API Document
Local: http://localhost:28000/docs

To deploy under a real domain/reverse-proxy path, set `ROOT_PATH` in `.env` (see `.env.example`) — the docs will then be served at `https://<your-domain>/<ROOT_PATH>/docs`.

> At the time of writing, parts of the API server are experimental, and hence subject to change.

## Deployment
* Docker
* nvidia-contianer-toolkit
* Requires the external network used by `docker-compose.yaml`/`I2PDM2-mysql`'s compose file to exist first: `docker network create pest_app_network`

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

* pytorch: (tested: 12.1, 12.4)
```bash
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```
* check out [requirements](requirements.txt) for other dependencies
* Docker
* nvidia-contianer-toolkit

### Tests

```bash
# test locally
bash ./scripts/test.sh
# Perform tests using deploy environment 
docker compose -f docker-compose.test.yaml up --build
```
### Format

```bash
bash ./scripts/format.sh
```
### Python linter check

```bash
bash ./scripts/lint.sh
```


