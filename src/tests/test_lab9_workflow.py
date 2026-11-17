"""Catch invalid workflow mappings before GitHub rejects all jobs."""
from pathlib import Path

import yaml


class UniqueKeysLoader(yaml.BaseLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f"duplicate YAML key {key!r} at line {key_node.start_mark.line + 1}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def test_lab9_workflows_have_no_duplicate_mapping_keys():
    workflows = Path(__file__).resolve().parents[2] / ".github" / "workflows"
    for path in workflows.glob("*.yml"):
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeysLoader)
        assert isinstance(data, dict) and isinstance(data.get("jobs"), dict), path.name


def test_lab9_duplicate_checkout_options_are_rejected():
    import pytest

    with pytest.raises(ValueError, match="duplicate YAML key 'with'"):
        yaml.load("steps:\n  - uses: checkout\n    with: {fetch-depth: 0}\n    with: {persist-credentials: false}\n",
                  Loader=UniqueKeysLoader)
