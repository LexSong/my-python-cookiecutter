import difflib
import importlib.metadata
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Annotated

import typer

TEMPLATE = Path(__file__).parent / "template"

app = typer.Typer(
    help="Scaffold and check my Python projects. Run `my-cookiecutter readme` for the full context: layout, tooling, "
    "and how to check a project."
)


def append(target: Path, text: str):
    # Text mode on Windows writes "\n" as "\r\n", but uv init writes LF, so
    # newline="" keeps the appended tables LF too.
    with target.open("a", encoding="utf-8", newline="") as f:
        f.write(text)


@app.command()
def add_formatter(path: Annotated[Path, typer.Argument()] = Path(".")):
    """Add my tool config to pyproject.toml in PATH. Needs no project table, so it also suits scripts that each carry their
    own dependencies in a PEP 723 block."""
    pyproject = path / "pyproject.toml"
    text = (TEMPLATE / "tools.toml").read_text(encoding="utf-8")
    if pyproject.exists():
        tables = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("tool", {})
        clash = [name for name in tomllib.loads(text)["tool"] if name in tables]
        if clash:
            typer.echo(f"{pyproject} already has [tool.{clash[0]}]", err=True)
            raise typer.Exit(1)
    else:
        # tools.toml starts with a blank line to follow existing tables, but
        # here it starts the file.
        text = text.lstrip("\n")

    path.mkdir(parents=True, exist_ok=True)
    append(pyproject, text)


@app.command()
def add_pre_commit(path: Annotated[Path, typer.Argument()] = Path(".")):
    """Add my pre-commit config to the git repo in PATH, and install its git hook."""
    config = path / ".pre-commit-config.yaml"
    if config.exists():
        typer.echo(f"{config} already exists", err=True)
        raise typer.Exit(1)
    # pre-commit runs from a git hook, so it needs a git repo, and creating one
    # is not this command's call.
    repo = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, capture_output=True, check=False)
    if repo.returncode != 0:
        typer.echo(f"{path} is not in a git repo", err=True)
        raise typer.Exit(1)

    # The template copy has no leading dot, so the wheel build does not skip it
    # as a hidden file.
    shutil.copyfile(TEMPLATE / "pre-commit-config.yaml", config)
    # A config file alone does nothing; pre-commit only runs once it has written
    # .git/hooks/pre-commit.
    subprocess.run(["pre-commit", "install"], cwd=path, check=True)


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
    # alone, so the project is not installed until `add-lib`. The template only
    # appends what every project shares.
    subprocess.run(["uv", "init", "--bare", "--vcs", "git", "--python", python, str(path)], check=True)
    add_formatter(path)
    add_pre_commit(path)

    # The index must be in pyproject.toml before `uv add`, or torch resolves
    # from PyPI, whose Windows wheels are CPU-only.
    if torch:
        append(pyproject, (TEMPLATE / "torch.toml").read_text(encoding="utf-8"))
        subprocess.run(["uv", "add", "torch", "torchvision"], cwd=path, check=True)


@app.command()
def add_lib():
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


def missing(template, project, key: str) -> list[str]:
    """List each setting in template that project lacks or sets to another value."""
    if isinstance(template, dict) and isinstance(project, dict):
        found = []
        for name, value in template.items():
            if name not in project:
                found.append(f"{key}.{name} is missing")
            else:
                found.extend(missing(value, project[name], f"{key}.{name}"))
        return found
    # A project may add its own entries, such as another index, so a list only
    # needs every entry the template has.
    if isinstance(template, list) and isinstance(project, list):
        return [f"{key} lacks {item}" for item in template if item not in project]
    if template != project:
        return [f"{key} is {project!r}, template has {template!r}"]
    return []


def check_environment(path: Path, project: dict) -> list[str]:
    found = []
    # A dependency string starts with the package name, such as "torch>=2.9".
    names = [re.split(r"[^\w.-]", dep, maxsplit=1)[0].lower() for dep in project["project"].get("dependencies", [])]
    if "torch" in names:
        torch = tomllib.loads((TEMPLATE / "torch.toml").read_text(encoding="utf-8"))
        found.extend(missing(torch["tool"], project.get("tool", {}), "tool"))

    # uv_build installs src/<name>/, so each needs the other. A one-file tool
    # uses flit_core and has no src/.
    backend = project.get("build-system", {}).get("build-backend")
    if (path / "src").is_dir() and backend is None:
        found.append("src/ exists but [build-system] is missing, so src/ is never installed")
    if backend == "uv_build" and not (path / "src").is_dir():
        found.append("uv_build has no src/ to build, so every `uv run` fails")
    return found


def check_formatting(path: Path, project: dict) -> list[str]:
    # Comparing parsed TOML ignores comments and taplo's formatting, so only
    # real setting differences show up.
    tools = tomllib.loads((TEMPLATE / "tools.toml").read_text(encoding="utf-8"))
    found = missing(tools["tool"], project.get("tool", {}), "tool")

    config = path / ".pre-commit-config.yaml"
    if not config.exists():
        found.append(".pre-commit-config.yaml is missing")
    else:
        # read_text turns CRLF into LF, so line endings never count as a difference.
        expected = (TEMPLATE / "pre-commit-config.yaml").read_text(encoding="utf-8").splitlines()
        actual = config.read_text(encoding="utf-8").splitlines()
        diff = list(difflib.unified_diff(expected, actual, "template", ".pre-commit-config.yaml", lineterm=""))
        if diff:
            found.append(".pre-commit-config.yaml differs from the template:\n" + "\n".join(diff))

    hook = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
        cwd=path,
        capture_output=True,
        text=True,
        check=True,
    )
    if not Path(hook.stdout.strip()).exists():
        found.append("the pre-commit hook is not installed; run `pre-commit install`")
    return found


@app.command()
def check(path: Annotated[Path, typer.Argument()] = Path(".")):
    """Show where the project in PATH differs from the template. Changes nothing. The formatting setup is checked only
    when git tracks .py files, and the environment only when pyproject.toml has a project table."""
    pyproject = path / "pyproject.toml"
    if not pyproject.exists():
        typer.echo(f"{pyproject} is missing")
        raise typer.Exit(1)
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    found = []
    if "project" in project:
        found.extend(check_environment(path, project))
    files = subprocess.run(["git", "ls-files", "*.py"], cwd=path, capture_output=True, text=True, check=True)
    if files.stdout.strip():
        found.extend(check_formatting(path, project))

    for line in found:
        typer.echo(line)
    if found:
        raise typer.Exit(1)


@app.command()
def readme():
    """Print the README: what my Python projects should look like, and why."""
    # The wheel build copies README.md into the package metadata, so the
    # installed tool carries the README that matches its own template.
    typer.echo(importlib.metadata.metadata("my-python-cookiecutter").json["description"])


def main():
    app()
