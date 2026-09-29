#!/bin/bash

set -euo pipefail

echo "Apply database migrations"
uv run --no-dev ./manage.py migrate

echo "Apply test mode schema migrations"
uv run --no-dev ./manage.py migrate --database=test_mode

echo "Create superuser"
uv run --no-dev ./manage.py createsuperuser --noinput || echo "Superuser already exists"

echo "Collect static files"
uv run --no-dev ./manage.py collectstatic --noinput

echo "Compile messages"
uv run --no-dev ./manage.py compilemessages

echo "Start gunicorn server"
uv run --no-dev gunicorn -c ./whimo/gunicorn.conf.py whimo.common.wsgi

exec "$@"
