# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from __future__ import annotations

import json
from pathlib import Path


def _load_agent_contract() -> dict:
    return json.loads(Path("docs/agent-contract.json").read_text())


def test_agent_contract_artifact_exists() -> None:
    assert Path("docs/agent-contract.json").exists()


def test_agent_contract_declares_cli_exception_for_trace_codegen() -> None:
    contract = _load_agent_contract()
    exceptions = contract["response_contract"]["success_exceptions"]
    assert any(item["command"] == "trace.codegen" for item in exceptions)


def test_agent_contract_declares_usage_exit_code() -> None:
    contract = _load_agent_contract()
    assert contract["response_contract"]["exit_codes"]["usage_error"] == 2


def test_agent_contract_does_not_expose_internal_doctor_all_action() -> None:
    contract = _load_agent_contract()
    doctor = next(item for item in contract["domains"] if item["name"] == "doctor")
    assert "all" not in doctor["actions"]


def test_agent_contract_error_codes_match_llms_txt() -> None:
    contract = _load_agent_contract()
    llms = Path("llms.txt").read_text()

    for item in contract["error_codes"]:
        assert item["code"] in llms


def test_agent_contract_error_codes_match_cli_reference() -> None:
    contract = _load_agent_contract()
    cli_reference = Path("docs/cli-reference.md").read_text()

    for item in contract["error_codes"]:
        assert item["code"] in cli_reference


def test_claude_md_mentions_trace_codegen_exception() -> None:
    text = Path("CLAUDE.md").read_text()
    assert "trace codegen" in text
    assert "raw text" in text or "Script written to" in text


def test_claude_md_mentions_llms_and_agent_contract() -> None:
    text = Path("CLAUDE.md").read_text()
    assert "llms.txt" in text
    assert "docs/agent-contract.json" in text


def test_openapi_artifact_exists() -> None:
    assert Path("docs/openapi.json").exists()


def test_openapi_uses_nullable_instead_of_json_schema_union_types() -> None:
    text = Path("docs/openapi.json").read_text()
    assert '"type": ["string", "null"]' not in text
    assert '"nullable": true' in text


def test_examples_artifacts_exist() -> None:
    assert Path("examples/calculator-e2e.sh").exists()
    assert Path("examples/trace-replay-codegen.sh").exists()
    assert Path("docs/agent-playbook.md").exists()
