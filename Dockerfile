FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends certbot python3-certbot-dns-cloudflare nginx openssl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash northssl

RUN mkdir -p /var/www/html \
    && mkdir -p /etc/nginx/default-cert /etc/nginx/sites-available /etc/nginx/sites-enabled \
    && rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-available/default \
    && openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout /etc/nginx/default-cert/privkey.pem \
        -out /etc/nginx/default-cert/fullchain.pem \
        -days 365 \
        -subj "/CN=localhost" \
    && touch /etc/nginx/sites-enabled/default.conf \
    && chown -R northssl:northssl /var/www/html

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /usr/local/bin/northssl-entrypoint.sh
RUN chmod +x /usr/local/bin/northssl-entrypoint.sh

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --upgrade pip \
    && pip install .

EXPOSE 8000
EXPOSE 80
EXPOSE 443

CMD ["/usr/local/bin/northssl-entrypoint.sh"]