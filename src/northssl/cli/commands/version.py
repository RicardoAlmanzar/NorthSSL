import typer

from northssl.core.version import get_northssl_version

def version_command() -> None:
    typer.echo(get_northssl_version())
