# Notes for coding agents

`my-cookiecutter` scaffolds my Python projects. Every machine installs it with
`uv tool install git+https://github.com/LexSong/my-python-cookiecutter`, so a
change reaches the installed tool only after a push. So unlike my other repos,
this one has a remote and wants pushes.

`app.py` leaves the name and Python version to `uv init --bare`. `addlib`
appends `[build-system]` instead of using `uv init --lib`. `template/` holds
only what every project shares, appended or copied as-is. Grow `template/`;
don't add a templating engine or a TOML writer.
