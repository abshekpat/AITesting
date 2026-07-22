import os

from dotenv import load_dotenv
from openai import OpenAI

from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric
from deepeval.models.llms import OpenRouterModel
from deepeval.test_case import LLMTestCase

# Walks up from the CWD to find and load the project-root .env, so the test
# runs regardless of where pytest is invoked from (including PyCharm's own
# runner, which starts with a clean environment).
load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"
JUDGE_MODEL_NAME = "openai/gpt-4o-mini"


def _groq_client() -> OpenAI:
    key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set in env / .env")
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

def ask_groq(question: str) -> str:
    """Send a single user message to Groq Llama-4 and return the raw text."""
    resp = _groq_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": question}],
        temperature=0.0,
    )
    return (resp.choices[0].message.content or "").strip()


def test_groq_llama4_basic_math():
    """Ask the simplest possible math question. GPT-4.1 judges the answer."""
    question = "What is 2+2? Reply with just the number."
    answer = ask_groq(question)
    print(f"\n[Groq {GROQ_MODEL}] → {answer!r}\n")

    case = LLMTestCase(
        input=question,
        actual_output=answer,
        expected_output="4",
        # HallucinationMetric scores actual_output against this grounding text.
        context=["Basic arithmetic fact: 2 + 2 = 4."],
    )

    judge = OpenRouterModel(
        model=JUDGE_MODEL_NAME,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    metrics = [
        AnswerRelevancyMetric(threshold=0.8, model=judge),
        HallucinationMetric(threshold=0.3, model=judge),
    ]

    assert_test(case, metrics)