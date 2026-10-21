FROM python:3.14-slim AS dependencies
COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/nexaassist
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-dev --extra evaluation

FROM python:3.14-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/nexaassist
COPY --from=dependencies /opt/nexaassist/.venv ./.venv
COPY app ./app
COPY evaluation/datasets/answer.jsonl ./evaluation/datasets/answer.jsonl
ENV PATH="/opt/nexaassist/.venv/bin:$PATH"
EXPOSE 8000
CMD ["ddtrace-run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
