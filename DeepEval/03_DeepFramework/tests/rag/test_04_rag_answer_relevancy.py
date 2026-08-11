"""RAG Metric #4: AnswerRelevancyMetric — does the answer stay on-topic for the
question? (higher is better)

Referenceless: reads input + actual_output only. A RAG bot can retrieve perfectly
yet still ramble or dodge — this catches that.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.answer_relevancy"]


@pytest.mark.rag
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_answer_relevancy(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(input=golden.input, actual_output=reply.answer)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
