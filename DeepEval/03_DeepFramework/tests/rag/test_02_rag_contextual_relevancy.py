"""RAG Metric #2: ContextualRelevancyMetric — are MOST of the retrieved chunks
on-topic for the question? (higher is better)

Referenceless on the answer side: it reads input + retrieval_context only, so it
catches a retriever that pulls noisy / off-topic chunks even when the final answer
happens to be fine.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.contextual_relevancy"]


@pytest.mark.rag
@pytest.mark.retrieval
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_contextual_relevancy(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply.answer,
        retrieval_context=reply.retrieval_context or [golden.expected_output],
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
