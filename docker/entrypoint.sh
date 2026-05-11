#!/bin/sh
set -eu

mkdir -p /var/www/html /etc/nginx/default-cert /etc/nginx/sites-available /etc/nginx/sites-enabled

nginx
exec uvicorn northssl.api.app:create_app --factory --host 0.0.0.0 --port 8000
