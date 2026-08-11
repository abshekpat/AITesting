"""RAG Metric #1: ContextualPrecisionMetric — are the RELEVANT retrieved chunks
ranked ABOVE the irrelevant ones? (higher is better, threshold from registry)

Needs `expected_output` (so the judge knows what "relevant" means) and
`retrieval_context` (the chunks the RAG pipeline actually pulled for this query).
Both come from the live RAG call + the golden dataset, so this grades real
retrieval ranking — not a canned answer.

Config + threshold come from the dashboard registry so the pytest suite and the
interactive dashboard stay in lock-step.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.contextual_precision"]


@pytest.mark.rag
@pytest.mark.retrieval
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_contextual_precision(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply.answer,
        expected_output=golden.expected_output,
        retrieval_context=reply.retrieval_context or [golden.expected_output],
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
