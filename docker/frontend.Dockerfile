FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /code

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --extra dev

COPY app ./app
COPY frontend/streamlit ./frontend/streamlit

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "frontend/streamlit/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
