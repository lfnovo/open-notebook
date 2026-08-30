"""Blind solver output optimization (schema + prompt). Validation unchanged.

Offline. Does not change acceptance, Blind independence, Cognitive, thresholds,
grounding rules, or Final Paper gates.
"""

from __future__ import annotations

import inspect

from open_notebook.graphs import question_paper as qp
from open_notebook.graphs.question_paper_blueprint import (
    empty_bank_cost_diagnostics,
    evaluate_blind_solver,
    parse_completion_usage_from_exc,
    parse_completion_usage_from_text,
    record_blind_solver_outcome,
)


def _solver_payload(**overrides):
    data = {
        "independently_derived_indices": [0],
        "option_analysis": [
            {"option": "A", "defensible": True},
            {"option": "B", "defensible": False},
            {"option": "C", "defensible": False},
            {"option": "D", "defensible": False},
            {"option": "E", "defensible": False},
        ],
        "information_sufficient": True,
        "arithmetic_consistent": True,
        "no_unsupported_claims": True,
        "terminology_grounded": True,
    }
    data.update(overrides)
    return data


class TestBlindSchemaReduced:
    def test_output_fields_are_validation_only(self):
        names = set(qp.BlindSolverOutput.model_fields)
        assert names == {
            "independently_derived_indices",
            "option_analysis",
            "information_sufficient",
            "arithmetic_consistent",
            "no_unsupported_claims",
            "terminology_grounded",
        }
        assert "solver_reasoning" not in names
        assert "terminology_issues" not in names
        assert set(qp.OptionDefensibility.model_fields) == {"option", "defensible"}

    def test_constructs_without_verbose_fields(self):
        out = qp.BlindSolverOutput.model_validate(_solver_payload())
        dumped = out.model_dump()
        assert "solver_reasoning" not in dumped
        assert "terminology_issues" not in dumped
        assert "reason" not in dumped["option_analysis"][0]

    def test_ignores_legacy_verbose_keys(self):
        payload = _solver_payload(
            solver_reasoning="long essay",
            terminology_issues=["QE", "M1"],
        )
        payload["option_analysis"][0]["reason"] = "verbose"
        out = qp.BlindSolverOutput.model_validate(payload)
        dumped = out.model_dump()
        assert "solver_reasoning" not in dumped
        assert dumped["independently_derived_indices"] == [0]
        assert dumped["option_analysis"][0]["defensible"] is True


class TestBlindPrompt:
    def test_system_asks_for_json_not_prose(self):
        src = qp.BLIND_SOLVER_SYSTEM
        assert "solver_reasoning" not in src
        assert "terminology_issues" not in src
        assert "brief reason" not in src.lower()
        assert "JSON only" in src or "structured JSON only" in src
        assert "No explanations" in src
        assert "Do not describe the solving process" in src
        assert "terminology_grounded" in src
        assert "independently" in src.lower() or "NOT seen the answer key" in src

    def test_user_prompt_is_concise(self):
        src = inspect.getsource(qp._blind_solve)
        assert "Analyse each option" not in src
        assert "JSON only" in src
        assert "solver_reasoning" not in src


class TestValidationUnchanged:
    def test_agree_still_passes(self):
        assert evaluate_blind_solver(_solver_payload(), [0], "single_correct") == []

    def test_disagree_still_fails(self):
        errors = evaluate_blind_solver(
            _solver_payload(independently_derived_indices=[1]),
            [0],
            "single_correct",
        )
        assert any("independent solver disagrees" in e for e in errors)

    def test_multiple_defensible_still_fails_single_correct(self):
        payload = _solver_payload()
        payload["option_analysis"][1]["defensible"] = True
        errors = evaluate_blind_solver(payload, [0], "single_correct")
        assert any("multiple defensible" in e for e in errors)

    def test_terminology_grounded_false_still_rejects(self):
        errors = evaluate_blind_solver(
            _solver_payload(terminology_grounded=False),
            [0],
            "single_correct",
        )
        assert any("untaught terminology" in e.lower() for e in errors)

    def test_unsupported_claims_still_reject(self):
        errors = evaluate_blind_solver(
            _solver_payload(no_unsupported_claims=False),
            [0],
            "single_correct",
        )
        assert any("unsupported" in e.lower() for e in errors)

    def test_none_still_fail_open(self):
        assert evaluate_blind_solver(None, [0], "single_correct") == []

    def test_legacy_reason_key_does_not_change_decision(self):
        compact = evaluate_blind_solver(_solver_payload(), [0], "single_correct")
        verbose = _solver_payload()
        for row in verbose["option_analysis"]:
            row["reason"] = "unused prose"
        verbose["solver_reasoning"] = "unused"
        verbose["terminology_issues"] = ["QE"]
        assert evaluate_blind_solver(verbose, [0], "single_correct") == compact


class TestBlindDiagnostics:
    def test_empty_cost_diagnostics_includes_counters(self):
        d = empty_bank_cost_diagnostics()
        assert d["blind_length_failures"] == 0
        assert d["blind_success_count"] == 0
        assert d["blind_completion_tokens"] == 0
        assert d["blind_reasoning_tokens"] == 0

    def test_record_success_and_length_failure(self):
        d = empty_bank_cost_diagnostics()
        record_blind_solver_outcome(
            d, success=True, completion_tokens=400, reasoning_tokens=120
        )
        record_blind_solver_outcome(
            d,
            success=False,
            length_failure=True,
            completion_tokens=2048,
            reasoning_tokens=2048,
        )
        assert d["blind_success_count"] == 1
        assert d["blind_length_failures"] == 1
        assert d["blind_completion_tokens"] == 2448
        assert d["blind_reasoning_tokens"] == 2168

    def test_record_none_diagnostics_is_safe(self):
        record_blind_solver_outcome(None, success=True, length_failure=True)

    def test_parse_length_finish_usage(self):
        blob = (
            "Could not parse response content as the length limit was reached - "
            "CompletionUsage(completion_tokens=2048, prompt_tokens=1298, "
            "total_tokens=3346, completion_tokens_details="
            "CompletionTokensDetails(reasoning_tokens=2048))"
        )
        comp, reason = parse_completion_usage_from_text(blob)
        assert comp == 2048
        assert reason == 2048

        err = RuntimeError(blob)
        err.__cause__ = type("LengthFinishReasonError", (Exception,), {})(
            "length limit was reached"
        )
        c2, r2 = parse_completion_usage_from_exc(err)
        assert c2 == 2048
        assert r2 == 2048

    def test_blind_solve_records_length_failure(self):
        src = inspect.getsource(qp._blind_solve)
        assert "record_blind_solver_outcome" in src
        assert "is_structured_output_length_error" in src
        assert "blind_success_count" not in inspect.getsource(qp._validate_cognitive_quality)


class TestUnchangedNeighbors:
    def test_cognitive_schema_still_has_reasons(self):
        assert "reasons" in qp.IndependentValidatorOutput.model_fields
        assert "criterion_scores" in qp.IndependentValidatorOutput.model_fields

    def test_blind_still_independent_and_2048(self):
        src = inspect.getsource(qp._blind_solve)
        assert "max_tokens=2048" in src
        assert "answer key" in qp.BLIND_SOLVER_SYSTEM
        gather = inspect.getsource(qp._validate_slot_independently)
        assert "asyncio.gather" in gather
        assert "_blind_solve" in gather
        assert "_validate_cognitive_quality" in gather

    def test_evaluate_blind_solver_source_unchanged_gates(self):
        src = inspect.getsource(evaluate_blind_solver)
        assert "independently_derived_indices" in src
        assert "terminology_grounded" in src
        assert "no_unsupported_claims" in src
        assert "information_sufficient" in src
        assert "if blind_solver is None:" in src
        assert "solver_reasoning" not in src
        assert "terminology_issues" not in src
