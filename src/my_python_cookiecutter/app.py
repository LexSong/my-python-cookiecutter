import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Annotated

import typer

TEMPLATE = Path(__file__).parent / "template"

app = typer.Typer()


def append(target: Path, text: str):
    # Text mode on Windows writes "\n" as "\r\n", but uv init writes LF, so
    # newline="" keeps the appended tables LF too.
    with target.open("a", encoding="utf-8", newline="") as f:
        f.write(text)


@app.command()
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

    # uv init writes everything that differs per project: name, requires-python
    # and git init. It also creates PATH if it does not exist yet, so every
    # later step runs inside PATH. --bare keeps pyproject.toml to [project]
    # alone, so the project is not installed until `addlib`. The template only
    # appends what every project shares.
    subprocess.run(["uv", "init", "--bare", "--vcs", "git", "--python", python, str(path)], check=True)
    # --frozen sets the version without locking or creating .venv.
    subprocess.run(["uv", "version", "0.0.0", "--frozen"], cwd=path, check=True)
    append(pyproject, (TEMPLATE / "tools.toml").read_text(encoding="utf-8"))

    # The index must be in pyproject.toml before `uv add`, or torch resolves
    # from PyPI, whose Windows wheels are CPU-only.
    if torch:
        append(pyproject, (TEMPLATE / "torch.toml").read_text(encoding="utf-8"))
        subprocess.run(["uv", "add", "torch", "torchvision"], cwd=path, check=True)

    # The template copy has no leading dot, so the wheel build does not skip it
    # as a hidden file.
    shutil.copyfile(TEMPLATE / "pre-commit-config.yaml", path / ".pre-commit-config.yaml")
    # A config file alone does nothing; pre-commit only runs once it has written
    # .git/hooks/pre-commit.
    subprocess.run(["pre-commit", "install"], cwd=path, check=True)


@app.command()
def addlib():
    """Add an empty src/<name>/ package and a uv_build build-system table to the project in the current directory."""
    pyproject = Path("pyproject.toml")
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    if "build-system" in project:
        typer.echo(f"{pyproject} already has [build-system]", err=True)
        raise typer.Exit(1)

    # uv_build looks for the project name with runs of -_. turned into one _.
    module = re.sub(r"[-_.]+", "_", project["project"]["name"]).lower()
    package = Path("src") / module
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").touch()

    # Same pin as `uv init --lib`: the installed uv's minor version, because
    # uv_build releases in step with uv.
    version = subprocess.run(["uv", "self", "version", "--short"], capture_output=True, text=True, check=True)
    major, minor = version.stdout.split(".")[:2]
    append(
        pyproject,
        f"""
[build-system]
requires = ["uv_build>={version.stdout.strip()},<{major}.{int(minor) + 1}.0"]
build-backend = "uv_build"
""",
    )


def main():
    app()
