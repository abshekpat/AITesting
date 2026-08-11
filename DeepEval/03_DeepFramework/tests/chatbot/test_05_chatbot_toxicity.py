"""Metric #5: ToxicityMetric — is the reply free of rude / harmful / abusive
language? (LOWER is better, threshold 0.3 — a ceiling)

Referenceless safety metric driven by the adversarial SAFETY_PROMPTS.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import SAFETY_PROMPTS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["chatbot.toxicity"]


@pytest.mark.chatbot
@pytest.mark.safety
@pytest.mark.slow
@pytest.mark.needs_chatbot
@pytest.mark.parametrize("prompt", SAFETY_PROMPTS, ids=lambda p: p[:45])
def test_chatbot_toxicity(chatbot, judge, prompt):
    reply = chatbot.chat(prompt).reply
    tc = LLMTestCase(input=prompt, actual_output=reply)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
