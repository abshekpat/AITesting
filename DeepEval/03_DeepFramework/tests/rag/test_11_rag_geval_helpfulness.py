"""RAG Metric #11: G-Eval Helpfulness — is the answer specific and actionable for
the question, rather than a generic dodge? (higher is better)

Referenceless rubric (input + actual_output). A RAG bot that retrieves the right
docs but answers with a vague "please contact support" to an in-scope question
should score low. Uses the `Helpfulness` G-Eval from the registry
(`rag.helpfulness`).
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.helpfulness"]


@pytest.mark.rag
@pytest.mark.geval
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_geval_helpfulness(rag, judge, golden):
    reply = rag.chat(golden.input)
    tc = LLMTestCase(input=golden.input, actual_output=reply.answer)
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
