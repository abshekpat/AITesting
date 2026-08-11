"""Metric #3: HallucinationMetric — does the reply contradict the ground-truth
context? (LOWER is better, threshold 0.4 — it's a ceiling)

DeepEval inverts the direction via is_successful(): a case passes when the
hallucination score is <= the threshold. Only goldens with a `context` are used.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import CHATBOT_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["chatbot.hallucination"]
GOLDENS = [g for g in CHATBOT_GOLDENS if g.context]


@pytest.mark.chatbot
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_chatbot
@pytest.mark.parametrize("golden", GOLDENS, ids=lambda g: g.input[:45])
def test_chatbot_hallucination(chatbot, judge, golden):
    reply = chatbot.chat(golden.input).reply
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply,
        context=golden.context,
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
