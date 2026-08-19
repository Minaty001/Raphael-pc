"""Regression tests for partial configuration persistence."""

import json

from raphael.core.configuration import RaphaelConfig


def test_save_overrides_merges_nested_sections(tmp_path):
    """Saving a later LLM choice must not erase earlier persisted choices."""
    config = RaphaelConfig()
    config.app.data_dir = str(tmp_path)

    config.save_overrides({"llm": {"primary_provider": "openai"}})
    config.save_overrides({"llm": {"openai_model": "gpt-4o"}})

    with open(tmp_path / "config.override.json", encoding="utf-8") as fh:
        assert json.load(fh) == {
            "llm": {
                "primary_provider": "openai",
                "openai_model": "gpt-4o",
            }
        }


def test_apply_overrides_restores_all_merged_llm_settings(tmp_path):
    config = RaphaelConfig()
    config.app.data_dir = str(tmp_path)
    config.save_overrides({"llm": {"primary_provider": "openai"}})
    config.save_overrides({"llm": {"openai_model": "gpt-4o"}})

    reloaded = RaphaelConfig()
    reloaded.app.data_dir = str(tmp_path)
    reloaded._apply_overrides()

    assert reloaded.llm.primary_provider == "openai"
    assert reloaded.llm.openai_model == "gpt-4o"
