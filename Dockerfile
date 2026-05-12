FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml config.yaml README.md ./
COPY shared/ shared/
COPY agents/ agents/

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["adk", "web", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--a2a", \
     "--session_service_uri", "memory://", \
     "--log_level", "info", \
     "agents"]
