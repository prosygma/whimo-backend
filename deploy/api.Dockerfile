FROM python:3.12 AS base

WORKDIR app

ADD https://astral.sh/uv/install.sh /uv-installer.sh

RUN sh /uv-installer.sh && \
    rm /uv-installer.sh && \
    apt update && \
    apt install -y gettext

ENV PATH="/root/.local/bin/:$PATH"

COPY pyproject.toml uv.lock ./

FROM base AS development

RUN uv sync --locked

COPY manage.py .

COPY locale locale

COPY whimo whimo

FROM base AS production

RUN uv sync --locked --no-dev

COPY manage.py .

COPY locale locale

COPY whimo whimo
