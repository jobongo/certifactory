#!/bin/sh
set -e

SSL_CERT_PATH="${SSL_CERT_PATH:-/etc/nginx/certs/cert.pem}"
SSL_KEY_PATH="${SSL_KEY_PATH:-/etc/nginx/certs/key.pem}"

if [ ! -f "$SSL_CERT_PATH" ] || [ ! -f "$SSL_KEY_PATH" ]; then
    echo "No SSL certificates found. Generating self-signed certificate..."
    mkdir -p "$(dirname "$SSL_CERT_PATH")"
    openssl req -x509 -nodes -days 365 \
        -newkey rsa:2048 \
        -keyout "$SSL_KEY_PATH" \
        -out "$SSL_CERT_PATH" \
        -subj "/CN=certifactory/O=Certifactory/C=US"
    echo "Self-signed certificate generated."
fi

export SSL_CERT_PATH SSL_KEY_PATH
envsubst '${SSL_CERT_PATH} ${SSL_KEY_PATH}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
