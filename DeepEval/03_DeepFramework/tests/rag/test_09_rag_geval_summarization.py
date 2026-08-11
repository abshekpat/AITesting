"""RAG Metric #9: G-Eval Summarization — when the RAG bot is asked to summarize a
policy, does its summary faithfully preserve the retrieved source? (higher is
better)

We ask the bot to summarize, then score the summary (`actual_output`) against the
chunks it retrieved (`input`) using a G-Eval rubric. A good summary is FAITHFUL
(every statement is supported by the source and nothing is invented) and captures
the main point the user asked about — brevity is expected, so leaving out
secondary details is fine. This is the G-Eval flavour of summarization — a custom
LLM rubric rather than DeepEval's built-in SummarizationMetric — built with the
same `_geval` pattern the registry uses so the judge model is injected at run time.
"""
import pytest
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

SUMMARY_TASKS = [
    "In two sentences, summarize your refund policy, including any timeframes.",
    "Summarize your shipping options and their costs in two short sentences.",
    "Briefly summarize what ShopSphere Plus includes and what it costs.",
]

_THRESHOLD = 0.5


def _summarization_metric(judge, threshold=_THRESHOLD):
    return GEval(
        name="SummarizationFaithfulness",
        criteria=(
            "`actual_output` is a short summary that answers the user, drawn from the "
            "source text in `input`. Score HIGH (toward 1.0) if every statement in the "
            "summary is supported by input (no fabricated or contradictory facts) AND it "
            "captures the main point the user asked about. Score LOW (toward 0.0) only if "
            "it invents facts absent from input, contradicts input, or misses the central "
            "point. Do NOT penalise it for omitting secondary details — brevity is expected."
        ),
        evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=judge,
        threshold=threshold,
    )


@pytest.mark.rag
@pytest.mark.geval
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("task", SUMMARY_TASKS, ids=lambda t: t[:45])
def test_rag_geval_summarization(rag, judge, task):
    reply = rag.chat(task)
    # The retrieved chunks ARE the source-of-truth being summarized.
    source = "\n".join(reply.retrieval_context) or reply.answer
    tc = LLMTestCase(input=source, actual_output=reply.answer)
    assert_test(tc, [_summarization_metric(judge)])
