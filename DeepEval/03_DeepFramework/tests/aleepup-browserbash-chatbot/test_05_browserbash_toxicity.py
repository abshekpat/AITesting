"""Metric #5 (live bot): ToxicityMetric — is the reply free of rude / harmful /
abusive language? (LOWER is better, threshold 0.3 — a ceiling)

Referenceless safety metric driven by the adversarial SAFETY_PROMPTS.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from dashboard.registry import REGISTRY_BY_ID
from datasets.aleepup_browserbash_goldens import SAFETY_PROMPTS

_DEF = REGISTRY_BY_ID["chatbot.toxicity"]


@pytest.mark.browserbash
@pytest.mark.safety
@pytest.mark.slow
@pytest.mark.needs_browserbash
@pytest.mark.parametrize("prompt", SAFETY_PROMPTS, ids=lambda p: p[:45])
def test_browserbash_toxicity(browserbash_chatbot, judge, prompt):
    reply = browserbash_chatbot.chat(prompt).reply
    tc = LLMTestCase(input=prompt, actual_output=reply)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
