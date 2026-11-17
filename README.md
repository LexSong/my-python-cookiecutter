# my-python-cookiecutter

This file states what my Python projects should look like.
`my-cookiecutter` writes the parts every project shares, and checks a project
against them. This file covers what the tool cannot decide.

Install or update the tool:

```bash
uv tool install git+https://github.com/LexSong/my-python-cookiecutter
uv tool upgrade my-python-cookiecutter
```

`my-cookiecutter --help` lists the commands. `init` copies and appends files from
`src/my_python_cookiecutter/template/`. That folder is the source of truth for
shared config, so compare against it, not against a copy in a document.

## Tooling

- **uv only.** I am moving every pixi project to uv. pixi files (`pixi.toml`,
  `pixi.lock`, `.pixi/`) mean a project still needs to be migrated.
- **Python version**: the newest one that every dependency ships wheels for. In
  2026-10 that is 3.14. CUDA packages set the limit; see the next section.

## CUDA on Windows

I work on Windows, and CUDA packages ship fewer Windows wheels than Linux ones.

- **Python version**: onnxruntime-gpu and triton-windows have no 3.15 `win_amd64`
  wheels, so Python stays on 3.14.
- **CUDA libraries**: in a pixi migration, CUDA libraries that came from conda become
  pip wheels, for example `onnxruntime-gpu[cuda,cudnn]`. Some NVIDIA wheels have no
  Windows build, so the lock needs
  `[tool.uv] required-environments = ["sys_platform == 'win32' and platform_machine == 'AMD64'"]`.
  division-2-face-tweaker is the working example.
- **Torch**: PyPI's Windows torch wheels are CPU-only, so torch and torchvision come
  from an explicit CUDA index. The template names the newest CUDA 13 index with
  Windows wheels. Check <https://download.pytorch.org/whl/> before bumping.
- **torchaudio** has no CUDA 13 Windows wheel. Avoid it, or accept the CPU build
  from PyPI.

## Layout

A project starts with scripts and dependencies. It gets `src/` and `[build-system]`
only when it needs them. Each state below is valid; any other mix is an error.

**1. Scripts and dependencies.** `my-cookiecutter init` writes this state:

```
pyproject.toml   [project] with dependencies, no [build-system]
scripts/         drivers, run with `uv run scripts/x.py`
```

Without `[build-system]`, uv treats the project as a list of dependencies and installs
nothing of its own. Create `scripts/` with the first script, because git does not track
an empty folder.

A PEP 723 block (`# /// script ... ///`) takes precedence over the project. When a script
carries one, `uv run` builds a separate environment from the block alone and ignores the
project `.venv`.

**2. Shared code.** When scripts need to share code, run `my-cookiecutter addlib`. It
adds an empty `src/<name>/__init__.py` and a `uv_build` `[build-system]`:

```
pyproject.toml   [build-system] = uv_build
src/<name>/      code the scripts share
scripts/         drivers that import src/<name>/
```

uv installs `src/<name>/` editable on every `uv sync`, so a script imports it with no
other config. The folder must match the project name; otherwise
`[tool.uv.build-backend] module-name` has to name it.

A command on PATH is a `[project.scripts]` entry pointing at a function in
`src/<name>/`. Add it by hand only when a tool must run outside the repo. Such a tool
lives in its own GitHub repo, is installed with
`uv tool install git+https://github.com/LexSong/<repo>`, and its AGENTS.md says it has
a remote and wants pushes.

**3. One file that must be installed.** A tool like yt-sub-txt is one `<name>.py` at
the root, but `uv tool install` still needs a build backend. `uv_build` only builds a
package folder, never a single file, so this case uses `flit_core` instead:

```toml
[build-system]
requires = ["flit_core>=4.1,<5"]
build-backend = "flit_core.buildapi"
```

### Errors

`src/` and `[build-system]` go together, so two mixes are always errors:

- `src/` without `[build-system]` never gets installed, so imports fail.
  `uv pip install -e .` appears to fix that, but it falls back to setuptools, writes
  nothing to `pyproject.toml` or `uv.lock`, and the next `uv sync` uninstalls it again.
- `uv_build` without `src/<name>/` fails to build, so every `uv run` stops, even for a
  script that imports nothing.

When code moves into or out of `src/`, change `[build-system]` in the same commit.

## Formatting

We rely on pre-commit for the final check: its hooks run the same formatters as
conform.nvim on every commit, so nothing else needs to enforce formatting. The config
file does nothing until `pre-commit install` has written the git hook; `init` runs it.
