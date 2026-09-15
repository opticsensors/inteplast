#!/usr/bin/env bash

set -e
set -x

coverage run -m pytest tests/ "$@"
coverage report
coverage html --title "Backend test coverage" --directory "${COVERAGE_HTML_DIR:-htmlcov}"
