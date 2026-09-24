"""docs/github-action.md only uses what really exists.

Every workflow in the document must be valid YAML, every `with:` key of the
action must be an input in action.yml, and every option passed to the CLI must
be an option of the real parser.
"""
import re
import shlex
from pathlib import Path

import yaml

from specsentinel.cli import build_parser

ROOT = Path(__file__).resolve().parent.parent
DOC = (ROOT / "docs" / "github-action.md").read_text(encoding="utf-8")
ACTION_INPUTS = set(yaml.safe_load((ROOT / "action.yml").read_text(encoding="utf-8"))["inputs"])
CLI_OPTIONS = {opt for action in build_parser()._actions for opt in action.option_strings}


def _workflows():
    blocks = re.findall(r"```yaml\n(.*?)```", DOC, flags=re.S)
    return [yaml.safe_load(block) for block in blocks]


def _steps():
    for workflow in _workflows():
        for job in workflow["jobs"].values():
            yield from job["steps"]


def test_document_exists_and_is_linked_from_the_readme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/github-action.md" in readme
    assert len(_workflows()) >= 2


def test_covers_version_pinning_baseline_and_path_filters():
    text = DOC.lower()
    for topic in ("pin", "baseline", "--include", "--exclude"):
        assert topic in text, topic


def test_action_inputs_exist():
    used = [step for step in _steps() if "specsentinel@" in str(step.get("uses", ""))]
    assert used, "at least one workflow uses the action"
    for step in used:
        assert re.search(r"@v\d+\.\d+\.\d+$|@[0-9a-f]{40}$", step["uses"]), "action ref is pinned"
        for key in step.get("with", {}):
            assert key in ACTION_INPUTS, f"unknown action input: {key}"


def test_cli_options_exist_and_install_is_pinned():
    runs = [step["run"] for step in _steps() if "run" in step]
    assert any(re.search(r"specsentinel==\d+\.\d+\.\d+", run) for run in runs), "pip install is pinned"
    checked = 0
    for run in runs:
        for line in run.replace("\\\n", " ").splitlines():
            if not line.strip().startswith("specsentinel "):
                continue
            for token in shlex.split(line.replace("${{", "").replace("}}", "")):
                if token.startswith("-"):
                    option = token.split("=", 1)[0]
                    assert option in CLI_OPTIONS, f"unknown CLI option: {option}"
                    checked += 1
    assert checked >= 4
