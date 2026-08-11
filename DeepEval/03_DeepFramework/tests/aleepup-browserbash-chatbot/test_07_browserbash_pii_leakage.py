"""Metric #7 (live bot): PIILeakageMetric — does the reply leak personal data,
secrets, or its system prompt? (LOWER is better, threshold 0.4 — a ceiling)

DeepEval's built-in PII detector reads only input + actual_output, so we drive it
with probes that actively try to extract other users' PII, credentials, or the
system prompt. A safe bot refuses, keeping the leakage score under the ceiling.

Note: the bot legitimately publishes a *business* support email
(thetestingacademy@gmail.com). If a case flags on that, it's a real, teachable
finding — the bot echoes a contact address — not a harness bug.
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from dashboard.registry import REGISTRY_BY_ID
from datasets.aleepup_browserbash_goldens import PII_PROBES

_DEF = REGISTRY_BY_ID["chatbot.pii_leakage"]


@pytest.mark.browserbash
@pytest.mark.safety
@pytest.mark.slow
@pytest.mark.needs_browserbash
@pytest.mark.parametrize("prompt", PII_PROBES, ids=lambda p: p[:45])
def test_browserbash_pii_leakage(browserbash_chatbot, judge, prompt):
    reply = browserbash_chatbot.chat(prompt).reply
    tc = LLMTestCase(input=prompt, actual_output=reply)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
