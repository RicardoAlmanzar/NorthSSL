from __future__ import annotations

from jinja2 import Environment, StrictUndefined

HTTPS_TEMPLATE = """
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {{ server_names | join(' ') }};

    ssl_certificate {{ certificate_path }};
    ssl_certificate_key {{ certificate_key_path }};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    {% if document_root %}
    root {{ document_root }};
    index index.html index.htm;
    {% endif %}

    location / {
        {% if proxy_pass_upstream %}
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_pass http://{{ proxy_pass_upstream }};
        {% else %}
        try_files $uri $uri/ =404;
        {% endif %}
    }
}
""".strip()

HTTP_REDIRECT_TEMPLATE = """
server {
    listen 80;
    listen [::]:80;
    server_name {{ server_names | join(' ') }};

    location ^~ /.well-known/acme-challenge/ {
        root {{ acme_webroot_path }};
        default_type "text/plain";
        try_files $uri =404;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
""".strip()


class NginxTemplateEngine:
    def __init__(self) -> None:
        self._environment = Environment(autoescape=False, undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)

    def render_https_site(
        self,
        *,
        server_names: list[str],
        certificate_path: str,
        certificate_key_path: str,
        document_root: str | None = None,
        proxy_pass_upstream: str | None = None,
        enable_redirect: bool = True,
    ) -> str:
        https_config = self._environment.from_string(HTTPS_TEMPLATE).render(
            server_names=server_names,
            certificate_path=certificate_path,
            certificate_key_path=certificate_key_path,
            document_root=document_root,
            proxy_pass_upstream=proxy_pass_upstream,
        )

        if not enable_redirect:
            return https_config

        redirect_config = self._environment.from_string(HTTP_REDIRECT_TEMPLATE).render(
            server_names=server_names,
            acme_webroot_path=document_root or "/var/www/html",
        )
        return f"{redirect_config}\n\n{https_config}\n"
