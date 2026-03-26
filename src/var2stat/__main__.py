#!/usr/bin/env python3

import click

from .config import config_command
from .generate import generate_command


@click.group()
def cli() -> None:
    """Convert variable fonts to static font instances."""
    pass


cli.add_command(config_command, name="config")
cli.add_command(generate_command, name="generate")


if __name__ == "__main__":
    cli()
