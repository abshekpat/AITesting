"""Metric #6: G-Eval Correctness — do the FACTS in the reply match the golden
expected_output? (higher is better, threshold 0.6)

Unlike AnswerRelevancy (referenceless), this metric DOES read expected_output, so
it actually grades the reply against the golden dataset. We reuse the exact GEval
rubric the dashboard uses for correctness (`_correctness` from the registry).
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import CHATBOT_GOLDENS
from dashboard.registry import _correctness

_THRESHOLD = 0.6


@pytest.mark.chatbot
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_chatbot
@pytest.mark.parametrize("golden", CHATBOT_GOLDENS, ids=lambda g: g.input[:45])
def test_chatbot_correctness(chatbot, judge, golden):
    reply = chatbot.chat(golden.input).reply
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply,
        expected_output=golden.expected_output,
    )
    assert_test(tc, [_correctness(judge, _THRESHOLD)])
