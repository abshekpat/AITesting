"""Metric #3 (live bot): HallucinationMetric — does the reply contradict the
ground-truth context? (LOWER is better, threshold 0.4 — a ceiling)

DeepEval inverts the direction: a case passes when the hallucination score is
<= the threshold. Only goldens that carry a ``context`` are used.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from dashboard.registry import REGISTRY_BY_ID
from datasets.aleepup_browserbash_goldens import BROWSERBASH_GOLDENS

_DEF = REGISTRY_BY_ID["chatbot.hallucination"]
GOLDENS = [g for g in BROWSERBASH_GOLDENS if g.context]


@pytest.mark.browserbash
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_browserbash
@pytest.mark.parametrize("golden", GOLDENS, ids=lambda g: g.input[:45])
def test_browserbash_hallucination(browserbash_chatbot, judge, golden):
    reply = browserbash_chatbot.chat(golden.input).reply
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply,
        context=golden.context,
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
