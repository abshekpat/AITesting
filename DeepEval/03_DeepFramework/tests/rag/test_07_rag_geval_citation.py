"""RAG Metric #7: G-Eval Citation Quality — does the answer cite a source filename
(e.g. [refund_policy.md]) that is actually present in `retrieval_context`?
(higher is better)

This is what separates a trustworthy RAG answer from a confident guess: the cited
source must exist among the retrieved chunks. Uses the `CitationQuality` G-Eval
rubric from the registry (`rag.citation_quality`).
"""
import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from datasets.rag_goldens import RAG_GOLDENS
from dashboard.registry import REGISTRY_BY_ID

_DEF = REGISTRY_BY_ID["rag.citation_quality"]


@pytest.mark.rag
@pytest.mark.geval
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("golden", RAG_GOLDENS, ids=lambda g: g.input[:45])
def test_rag_geval_citation(rag, judge, golden):
    reply = rag.chat(golden.input)
    # Prefer the real source filenames the pipeline returned; fall back to the
    # retrieved chunks (and finally the golden) so the metric always has context.
    retrieval_context = reply.sources or reply.retrieval_context or [golden.expected_output]
    tc = LLMTestCase(
        input=golden.input,
        actual_output=reply.answer,
        retrieval_context=retrieval_context,
    )
    assert_test(tc, [_DEF.factory(judge, _DEF.threshold)])
