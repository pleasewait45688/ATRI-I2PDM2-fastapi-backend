#!/usr/bin/env bash

set -e
set -x
# coverage run -m pytest -s -v --log-cli-level=DEBUG | tee results4.log
coverage run --source=app -m pytest -s -v -o log_cli=true
coverage report --show-missing
coverage html --title "${@-coverage}"