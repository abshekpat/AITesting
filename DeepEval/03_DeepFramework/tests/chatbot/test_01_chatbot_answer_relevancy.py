"""Metric #1: AnswerRelevancyMetric — does the reply stay on-topic for the question?

Parametrized so each golden becomes its own test case. Run with ``deepeval test run``
to capture every case and (when CONFIDENT_API_KEY is set) push the results to the
Confident AI cloud dashboard. The judge LLM and the chatbot target come from the
conftest fixtures, so the .env / JUDGE_PROVIDER selection and the golden dataset are
all honoured.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from datasets.chatbot_goldens import CHATBOT_GOLDENS


@pytest.mark.chatbot
@pytest.mark.quality
@pytest.mark.slow
@pytest.mark.needs_chatbot
@pytest.mark.parametrize("golden", CHATBOT_GOLDENS, ids=lambda g: g.input[:45])
def test_chatbot_answer_relevancy(chatbot, judge, golden):
    reply = chatbot.chat(golden.input).reply
    tc = LLMTestCase(input=golden.input, actual_output=reply)
    metric = AnswerRelevancyMetric(threshold=0.7, model=judge, include_reason=True)
    assert_test(tc, [metric])
