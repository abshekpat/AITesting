"""RAG Metric #3: FaithfulnessMetric — is every claim in the answer backed by the
chunks the RAG pipeline actually retrieved? (higher is better)

This is the core RAG hallucination guard: the answer must not invent facts that
are absent from `retrieval_context`. We feed the LIVE retrieved context (not the
golden) so we're grading the generator against what it was actually given.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.faithfulness"]


@pytest.mark.rag
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_faithfulness(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply.answer,
        retrieval_context=reply.retrieval_context or [golden.expected_output],
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
