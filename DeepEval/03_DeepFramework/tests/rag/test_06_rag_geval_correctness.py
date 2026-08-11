"""RAG Metric #6: G-Eval Correctness — do the FACTS in the answer match the golden
`expected_output`? (higher is better)

Unlike AnswerRelevancy (referenceless), this reads expected_output, so it actually
grades the answer against the golden dataset. Reuses the exact `Correctness` G-Eval
rubric the dashboard uses (`rag.correctness` in the registry).
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.correctness"]


@pytest.mark.rag
@pytest.mark.geval
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_geval_correctness(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply.answer,
        expected_output=golden.expected_output,
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
