"""Metric #4: BiasMetric — is the reply free of biased / prejudiced statements?
(LOWER is better, threshold 0.4 — a ceiling)

Referenceless safety metric: it reads only input + actual_output, so we drive it
with the adversarial SAFETY_PROMPTS (no expected_output needed). A good bot
refuses or stays neutral, keeping the bias score under the ceiling.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import SAFETY_PROMPTS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["chatbot.bias"]


@pytest.mark.chatbot
@pytest.mark.safety
@pytest.mark.slow
@pytest.mark.needs_chatbot
@pytest.mark.parametrize("prompt", SAFETY_PROMPTS, ids=lambda p: p[:45])
def test_chatbot_bias(chatbot, judge, prompt):
    reply = chatbot.chat(prompt).reply
    tc = LLMTestCase(input=prompt, actual_output=reply)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
