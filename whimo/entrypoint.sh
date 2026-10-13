#!/bin/bash

set -euo pipefail

echo "Apply database migrations"
poetry run ./manage.py migrate

echo "Apply test mode schema migrations"
poetry run ./manage.py migrate --database=test_mode

echo "Create superuser"
poetry run ./manage.py createsuperuser --noinput || echo "Superuser already exists"

echo "Collect static files"
poetry run ./manage.py collectstatic --noinput

echo "Compile messages"
poetry run ./manage.py compilemessages

echo "Start gunicorn server"
poetry run gunicorn -c ./whimo/gunicorn.conf.py whimo.common.wsgi

exec "$@"
