"""Metric #6 (live bot): G-Eval Correctness — do the FACTS in the reply match the
golden expected_output? (higher is better, threshold 0.6)

Unlike AnswerRelevancy (referenceless), this metric DOES read expected_output,
so it grades the live reply against the bootstrapped golden answers. We reuse the
exact GEval rubric the dashboard uses for correctness (``_correctness``).
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from dashboard.registry import _correctness
from datasets.aleepup_browserbash_goldens import BROWSERBASH_GOLDENS

_THRESHOLD = 0.6


@pytest.mark.browserbash
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_browserbash
@pytest.mark.parametrize("golden", BROWSERBASH_GOLDENS, ids=lambda g: g.input[:45])
def test_browserbash_correctness(browserbash_chatbot, judge, golden):
    reply = browserbash_chatbot.chat(golden.input).reply
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply,
        expected_output=golden.expected_output,
    )
    assert_test(tc, [_correctness(judge, _THRESHOLD)])
