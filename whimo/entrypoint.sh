#!/bin/bash

echo "Apply database migrations"
poetry run ./manage.py migrate

echo "Create superuser"
poetry run ./manage.py createsuperuser --noinput

echo "Collect static files"
poetry run ./manage.py collectstatic --noinput

echo "Compile messages"
poetry run ./manage.py compilemessages

echo "Start gunicorn server"
poetry run gunicorn -c ./whimo/gunicorn.conf.py whimo.common.wsgi

exec "$@"
