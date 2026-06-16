FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY filepilot ./filepilot

RUN pip install --no-cache-dir ".[mcp]" \
    && mkdir -p /workspace

CMD ["filepilot-mcp", "--allow", "/workspace", "--read-only"]
