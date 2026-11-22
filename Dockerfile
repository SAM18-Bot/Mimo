FROM python:3.11-slim
WORKDIR /app
COPY requirements_server.txt .
RUN --mount=type=secret,id=pip_ca \
    if [ -f /run/secrets/pip_ca ]; then export PIP_CERT=/run/secrets/pip_ca; fi && \
    pip install --no-cache-dir -r requirements_server.txt
COPY . .
ENV NO_HARDWARE=1 NO_VOICE=1 MIMO_ENV=production PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
