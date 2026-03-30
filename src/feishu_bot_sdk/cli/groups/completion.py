from __future__ import annotations

import click
from click.shell_completion import get_completion_class

from ..runtime.output import _print_result


@click.command("completion", help="Generate shell completion scripts")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish", "powershell"]))
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "pretty", "human"]),
    default="json",
    show_default=True,
    help="Output format",
)
def completion_command(shell: str, output_format: str) -> None:
    from ..app import app

    completion_class = get_completion_class(shell)
    if completion_class is None:
        raise ValueError(f"unsupported shell: {shell}")
    complete_var = "_FEISHU_COMPLETE"
    completer = completion_class(cli=app, ctx_args={}, prog_name="feishu", complete_var=complete_var)
    script = completer.source()
    _print_result({"shell": shell, "script": script}, output_format=output_format)


__all__ = ["completion_command"]
