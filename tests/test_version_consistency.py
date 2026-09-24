import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "pyproject.toml must contain a top level version"
    return match.group(1)


def _package_version() -> str:
    text = (ROOT / "src" / "specsentinel" / "__init__.py").read_text()
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    assert match, "src/specsentinel/__init__.py must define __version__"
    return match.group(1)


def _action_pinned_versions() -> list[str]:
    text = (ROOT / "action.yml").read_text()
    return re.findall(r"specsentinel==([0-9][^\"\s]*)", text)


def test_pyproject_and_package_version_match() -> None:
    assert _package_version() == _pyproject_version()


def test_action_pinned_version_matches_project() -> None:
    pinned = _action_pinned_versions()
    if not pinned:
        return
    project = _pyproject_version()
    for version in pinned:
        assert version == project, (
            f"action.yml installs specsentinel=={version} but the project "
            f"version is {project}. Pin the action to the released version."
        )