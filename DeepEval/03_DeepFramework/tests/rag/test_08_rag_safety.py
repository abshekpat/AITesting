"""RAG Metric #8: Safety — Bias + Toxicity. (LOWER is better — both thresholds
are ceilings)

Referenceless safety metrics: they read input + actual_output only, so we drive
the RAG bot with the shared adversarial SAFETY_PROMPTS (no expected_output). A
grounded RAG bot should refuse or stay neutral — "I don't have information on
that" — keeping bias and toxicity under their registry ceilings. Both metrics run
on every prompt in a single assert_test.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import SAFETY_PROMPTS
from dashboard.registry import REGISTRY_BY_ID

_BIAS = REGISTRY_BY_ID["rag.bias"]
_TOX = REGISTRY_BY_ID["rag.toxicity"]


@pytest.mark.rag
@pytest.mark.safety
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("prompt", SAFETY_PROMPTS, ids=lambda p: p[:45])
def test_rag_safety(rag, judge, prompt):
    reply = rag.chat(prompt)
    tc = LLMTestCase(input=prompt, actual_output=reply.answer)
    assert_test(tc, [
        _BIAS.factory(judge, _BIAS.threshold),
        _TOX.factory(judge, _TOX.threshold),
    ])
