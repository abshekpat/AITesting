"""Metric #4 (live bot): BiasMetric — is the reply free of biased / prejudiced
statements? (LOWER is better, threshold 0.4 — a ceiling)

Referenceless safety metric: reads only input + actual_output, so we drive it
with the adversarial SAFETY_PROMPTS (no expected_output). A good bot refuses or
stays neutral, keeping the bias score under the ceiling.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from dashboard.registry import REGISTRY_BY_ID
from datasets.aleepup_browserbash_goldens import SAFETY_PROMPTS

_DEF = REGISTRY_BY_ID["chatbot.bias"]


@pytest.mark.browserbash
@pytest.mark.safety
@pytest.mark.slow
@pytest.mark.needs_browserbash
@pytest.mark.parametrize("prompt", SAFETY_PROMPTS, ids=lambda p: p[:45])
def test_browserbash_bias(browserbash_chatbot, judge, prompt):
    reply = browserbash_chatbot.chat(prompt).reply
    tc = LLMTestCase(input=prompt, actual_output=reply)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
