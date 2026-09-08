FROM python:3.12 AS base

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PATH="/root/.local/bin:$PATH"

RUN apt update && \
    apt install -y gettext curl && \
    curl -sSL https://install.python-poetry.org | python3 -

COPY pyproject.toml poetry.lock ./

FROM base AS development

RUN poetry install --no-root

COPY manage.py .

COPY locale locale

COPY whimo whimo

FROM base AS production

RUN poetry install --without dev --no-root

COPY manage.py .

COPY locale locale

COPY whimo whimo
