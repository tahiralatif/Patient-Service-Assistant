FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first so Docker can cache this layer.
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Then copy the application code and the knowledge base.
COPY app ./app
COPY knowledge ./knowledge
COPY main.py ./

# Run as a non-root user.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]