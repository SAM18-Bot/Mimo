FROM cgr.dev/chainguard/wolfi-base@sha256:5172a213d2bba8b1c9ca11957db65562b52b0f9844583a0347318ea5fd8e3aa5
ENV PATH="/opt/venv/bin:${PATH}"
WORKDIR /opt/mimo
COPY requirements_server.txt .
RUN --mount=type=secret,id=pip_ca,target=/tmp/mimo-build-ca.pem,mode=0444 \
    if [ -f /tmp/mimo-build-ca.pem ]; then export SSL_CERT_FILE=/tmp/mimo-build-ca.pem PIP_CERT=/tmp/mimo-build-ca.pem; fi && \
    apk --no-cache upgrade && \
    apk add --no-cache python-3.11 libpq-18 libstdc++ tzdata && \
    apk add --no-cache --virtual .build-deps gcc glibc-dev python-3.11-dev postgresql-18-dev py3.11-pip && \
    python3.11 -m venv --without-pip /opt/venv && \
    /usr/bin/python3.11 -m pip --python /opt/venv/bin/python install --no-cache-dir pip==26.3 setuptools==84.2.1 && \
    python -m pip install --no-cache-dir --no-binary=psycopg2-binary -r requirements_server.txt && \
    python -m pip check && \
    apk del --no-network .build-deps
COPY server/ server/
COPY web/ web/
COPY main.py run_server.py alembic.ini ./
# Preserve the existing SQLite directory and launcher paths. Root owns the
# source and compatibility links, and the service can create its data files.
RUN addgroup -S -g 10001 mimo && adduser -S -D -u 10001 -G mimo mimo && \
    chmod -R a+rX,go-w /opt/mimo && \
    install -d -m 1775 -o root -g mimo /app && ln -s /opt/mimo/* /app/ && \
    ln -s /app/.env /opt/mimo/.env
WORKDIR /app
USER 10001:10001
ENV NO_HARDWARE=1 NO_VOICE=1 MIMO_ENV=production PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn --app-dir /opt/mimo main:app --host 0.0.0.0 --port ${PORT:-8000}"]
