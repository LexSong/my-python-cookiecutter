import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

TEMPLATE = Path(__file__).parent / "template"


def init(python: str = "3.14", torch: Annotated[bool, typer.Option("--torch")] = False):
    """Scaffold a uv package in the current directory, with my tool config and pre-commit."""
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        typer.echo("pyproject.toml already exists", err=True)
        raise typer.Exit(1)

    # uv init writes everything that differs per project: name, requires-python,
    # .python-version, src/ layout, git init, and a uv_build pin matching the
    # installed uv. The template only appends what every project shares.
    subprocess.run(["uv", "init", "--package", "--no-readme", "--python", python], check=True)
    append(pyproject, TEMPLATE / "tools.toml")

    # The index must be in pyproject.toml before `uv add`, or torch resolves
    # from PyPI, whose Windows wheels are CPU-only.
    if torch:
        append(pyproject, TEMPLATE / "torch.toml")
        subprocess.run(["uv", "add", "torch", "torchvision"], check=True)

    # The template copy has no leading dot, so the wheel build does not skip it
    # as a hidden file.
    shutil.copyfile(TEMPLATE / "pre-commit-config.yaml", ".pre-commit-config.yaml")
    # A config file alone does nothing; pre-commit only runs once it has written
    # .git/hooks/pre-commit.
    subprocess.run(["pre-commit", "install"], check=True)


def append(target: Path, source: Path):
    with target.open("a", encoding="utf-8") as f:
        f.write(source.read_text(encoding="utf-8"))


def main():
    typer.run(init)
