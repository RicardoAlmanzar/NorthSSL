# NorthSSL

NorthSSL is a modular, cross-platform SSL/TLS automation platform built on top of existing ACME tooling.

## MVP Scope

- Linux only at first
- Ubuntu / Debian
- Nginx
- Certbot
- CLI-first workflow

## Architecture Direction

- `core`: domain models, contracts, and application services
- `providers`: ACME and certificate provider adapters
- `platforms`: OS detection and platform-specific adapters
- `webservers`: integrations for Nginx, Apache, and future servers
- `cli`: Typer-based command line interface
- `database`: SQLite and SQLAlchemy foundation
- `dashboard`: FastAPI-based web layer for the future
- `utils`: safe subprocess and logging helpers

## First Command

After installing dependencies, run:

```bash
northssl doctor
```

This command reports the local platform and whether `nginx` and `certbot` are discoverable on the system.
