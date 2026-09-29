# Local development image for the admin e2e suite.
#
# Deliberately not deploy/api.Dockerfile: that one runs `apt update` and pipes
# install.python-poetry.org through the network, both of which are unusably slow
# on this machine. Everything here comes from PyPI, which is fast.
#
# Trade-off: no `gettext`, so `manage.py compilemessages` is unavailable and the
# locale/*.po catalogues fall back to English. The admin is unaffected.

FROM python:3.12

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install --no-cache-dir "poetry>=2.0,<3"

COPY pyproject.toml poetry.lock ./

# Dev group included: the e2e seed command reuses tests/factories (factory-boy).
RUN poetry install --no-root

COPY manage.py .
COPY locale locale
COPY whimo whimo
