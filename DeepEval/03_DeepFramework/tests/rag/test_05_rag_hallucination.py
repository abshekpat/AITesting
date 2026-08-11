"""RAG Metric #5: HallucinationMetric — does the answer CONTRADICT the ground
truth? (LOWER is better — threshold is a ceiling)

RagGolden has no `context` field (only ChatbotGolden does), so — exactly like the
dashboard runner — we use the golden's `expected_output` as the ground-truth
context to check the answer against. A case passes when the hallucination score
stays at/under the registry threshold.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.hallucination"]


@pytest.mark.rag
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_hallucination(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply.answer,
        context=[golden.expected_output],
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
