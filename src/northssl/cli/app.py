import typer

from northssl.cli.commands.doctor import doctor_app
from northssl.cli.commands.inspect import inspect_command
from northssl.cli.commands.issue import issue_command
from northssl.cli.commands.list import list_command
from northssl.cli.commands.revoke import revoke_command
from northssl.cli.commands.status import status_command
from northssl.cli.commands.version import version_command
from northssl.core.bootstrap import initialize_context

app = typer.Typer(
    add_completion=False,
    help="NorthSSL CLI for certificate automation.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

@app.callback()
def main(ctx: typer.Context) -> None:
    ctx.obj = initialize_context()

app.command("version")(version_command)
app.command("status")(status_command)
app.command("issue")(issue_command)
app.command("list")(list_command)
app.command("inspect")(inspect_command)
app.command("revoke")(revoke_command)
app.add_typer(doctor_app, name="doctor")
