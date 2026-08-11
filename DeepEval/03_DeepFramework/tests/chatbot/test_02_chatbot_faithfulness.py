"""Metric #2: FaithfulnessMetric — is every claim in the reply backed by the
ground-truth context? (higher is better, threshold 0.7)

Config + threshold come straight from the dashboard registry so the pytest suite
and the interactive dashboard stay in lock-step. Only goldens that carry a
ground-truth `context` are used — faithfulness needs a retrieval_context to check
the reply against.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import CHATBOT_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["chatbot.faithfulness"]
GOLDENS = [g for g in CHATBOT_GOLDENS if g.context]


@pytest.mark.chatbot
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_chatbot
@pytest.mark.parametrize("golden", GOLDENS, ids=lambda g: g.input[:45])
def test_chatbot_faithfulness(chatbot, judge, golden):
    reply = chatbot.chat(golden.input).reply
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply,
        retrieval_context=golden.context,
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
