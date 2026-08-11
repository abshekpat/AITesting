"""RAG Metric #10: Conversational — ConversationCompletenessMetric. (higher is
better)

Drives the RAG bot through a multi-turn conversation (each turn carries the prior
history) and checks the bot satisfied the user's intent across the whole thread,
not just the last message. Built as a ConversationalTestCase of `Turn`s (the shape
DeepEval 3.x expects — one Turn per user message and per assistant reply, the
assistant turns carrying their retrieval_context) and measured directly (assert on
`is_successful()`), since conversational cases don't go through the single-case
`assert_test` path.
"""
import pytest
from deepeval.metrics import ConversationCompletenessMetric
from deepeval.test_case import ConversationalTestCase, Turn

_THRESHOLD = 0.5

RAG_CONVERSATIONS = [
    [
        "How long do refunds take?",
        "And how will I get the money back?",
        "What about credit cards specifically?",
    ],
    [
        "I want to return a hoodie I bought.",
        "How long do I have to start the return?",
        "Will the refund go back to my card?",
    ],
]


@pytest.mark.rag
@pytest.mark.conversational
@pytest.mark.slow
@pytest.mark.needs_rag
@pytest.mark.parametrize("convo", RAG_CONVERSATIONS, ids=lambda c: c[0][:45])
def test_rag_conversational(rag, judge, convo):
    history: list[dict] = []
    turns: list[Turn] = []
    for user_msg in convo:
        reply = rag.chat(user_msg, history=history)
        turns.append(Turn(role="user", content=user_msg))
        turns.append(Turn(
            role="assistant",
            content=reply.answer,
            retrieval_context=reply.retrieval_context or None,
        ))
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": reply.answer})

    ctc = ConversationalTestCase(turns=turns)
    metric = ConversationCompletenessMetric(threshold=_THRESHOLD, model=judge, include_reason=True)
    metric.measure(ctc)
    assert metric.is_successful(), metric.reason
