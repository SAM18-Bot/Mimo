FROM python:3.11-slim-trixie
WORKDIR /app
COPY requirements_server.txt .
RUN --mount=type=secret,id=pip_ca,target=/tmp/mimo-build-ca.pem,mode=0444 \
    if [ -f /tmp/mimo-build-ca.pem ]; then export PIP_CERT=/tmp/mimo-build-ca.pem; fi && \
    ca_bundle="${PIP_CERT:-/etc/ssl/certs/ca-certificates.crt}" && \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get -o Acquire::https::CaInfo="$ca_bundle" update --error-on=any && \
    DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::https::CaInfo="$ca_bundle" -y --no-install-recommends upgrade && \
    rm -rf /var/lib/apt/lists/* && \
    python -m pip install --no-cache-dir --upgrade pip==26.3 setuptools==84.2.1 && \
    python -m pip install --no-cache-dir -r requirements_server.txt
COPY . .
ENV NO_HARDWARE=1 NO_VOICE=1 MIMO_ENV=production PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
