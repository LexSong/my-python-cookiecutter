import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

TEMPLATE = Path(__file__).parent / "template"


def init(
    path: Annotated[Path, typer.Argument()] = Path("."),
    python: str = "3.14",
    torch: Annotated[bool, typer.Option("--torch")] = False,
):
    """Scaffold a uv project in PATH, with my tool config and pre-commit. Like `uv init`, PATH defaults to the current
    directory and names the project."""
    pyproject = path / "pyproject.toml"
    if pyproject.exists():
        typer.echo(f"{pyproject} already exists", err=True)
        raise typer.Exit(1)

    # uv init writes everything that differs per project: name, requires-python,
    # .python-version, src/<name>/, git init, and a uv_build pin matching the
    # installed uv. It also creates PATH if it does not exist yet, so every later
    # step runs inside PATH. The template only appends what every project shares.
    # --lib writes [build-system] but no [project.scripts] command: scripts go in
    # scripts/ and import src/<name>/, which uv installs editable on every sync.
    subprocess.run(["uv", "init", "--lib", "--no-readme", "--python", python, str(path)], check=True)
    append(pyproject, TEMPLATE / "tools.toml")

    # The index must be in pyproject.toml before `uv add`, or torch resolves
    # from PyPI, whose Windows wheels are CPU-only.
    if torch:
        append(pyproject, TEMPLATE / "torch.toml")
        subprocess.run(["uv", "add", "torch", "torchvision"], cwd=path, check=True)

    # The template copy has no leading dot, so the wheel build does not skip it
    # as a hidden file.
    shutil.copyfile(TEMPLATE / "pre-commit-config.yaml", path / ".pre-commit-config.yaml")
    # A config file alone does nothing; pre-commit only runs once it has written
    # .git/hooks/pre-commit.
    subprocess.run(["pre-commit", "install"], cwd=path, check=True)


def append(target: Path, source: Path):
    with target.open("a", encoding="utf-8") as f:
        f.write(source.read_text(encoding="utf-8"))


def main():
    typer.run(init)
