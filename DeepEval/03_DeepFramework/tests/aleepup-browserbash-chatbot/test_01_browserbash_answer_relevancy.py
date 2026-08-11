"""Metric #1 (live bot): AnswerRelevancyMetric — does the reply stay on-topic
for the question? (higher is better, threshold 0.7)

Referenceless: reads only input + actual_output. Each golden becomes its own
parametrized case. Target = the live BrowserBash bot; judge = OpenAI gpt-5-mini.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from datasets.aleepup_browserbash_goldens import BROWSERBASH_GOLDENS


@pytest.mark.browserbash
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_browserbash
@pytest.mark.parametrize("golden", BROWSERBASH_GOLDENS, ids=lambda g: g.input[:45])
def test_browserbash_answer_relevancy(browserbash_chatbot, judge, golden):
    reply = browserbash_chatbot.chat(golden.input).reply
    tc = LLMTestCase(input=golden.input, actual_output=reply)
    metric = AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=True)
    assert_test(tc, [metric])
