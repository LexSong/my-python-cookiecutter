# Notes for coding agents

`my-cookiecutter` scaffolds my Python projects. Every machine installs it with
`uv tool install git+https://github.com/LexSong/my-python-cookiecutter`, so a
change reaches the installed tool only after a push. So unlike my other repos,
this one has a remote and wants pushes.

`init.py` leaves everything that differs per project (name, Python version,
layout, the `uv_build` pin) to `uv init`. `template/` holds only what every
project shares, appended or copied as-is. Grow `template/`; don't add a
templating engine.
