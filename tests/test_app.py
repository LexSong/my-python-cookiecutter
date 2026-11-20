import pytest

from my_python_cookiecutter.app import iter_requires_python_issues


# Each case lists one text per expected issue, which that issue must contain.
# The specs assume PYTHON_VERSION is 3.14.
@pytest.mark.parametrize(
    ("spec", "texts"),
    [
        (">=3.14", []),
        (">=3.14.1", []),
        (">=3.14,<3.15", []),
        (">=3.14, <3.15", []),
        (">=3.13,<3.14", ["Consider raising it"]),
        (">=3.10", ["Consider raising it"]),
        (None, ["missing"]),
        ("==3.14", ["write a range"]),
        ("==3.13.*", ["write a range"]),
        ("~=3.14", ["write a range"]),
        ("<4", ["write a range"]),
        ("<3.15,>=3.14", ["write a range"]),
    ],
)
def test_iter_requires_python_issues(spec, texts):
    issues = list(iter_requires_python_issues(spec))
    assert len(issues) == len(texts)
    for issue, text in zip(issues, texts):
        assert text in issue
