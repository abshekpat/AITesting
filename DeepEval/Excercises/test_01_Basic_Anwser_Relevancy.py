# Exercise 1 (Basic): Answer Relevancy & Hallucination Detection
# Level Basic : chatbot anwsers

# Goal:
#     Learn the two most fundamental LLM evaluation metrics:
#     1. Answer Relevancy  — Does the chatbot answer the question asked?
#     2. Hallucination      — Does the chatbot make up facts not in the context?


# Setup:
    # export GROQ_API_KEY=your_key_here
    # export OPENROUTER_API_KEY=your_key_here   # DeepEval uses this for judging


import os
import sys
import requests # this module will help us to fetch the chat from the chat Ui
# We can make the API request via the requests module.
from dotenv import load_dotenv
from deepeval.test_case import LLMTestCase
from deepeval import assert_test
from deepeval.metrics import AnswerRelevancyMetric, HallucinationMetric
from deepeval.models.llms import OpenRouterModel

# Walks up from the CWD to find and load the project-root .env, so the test
# runs regardless of where pytest is invoked from.
load_dotenv()

JUDGE_MODEL_NAME = "openai/gpt-4o-mini"

def test_hello_world():

    test = LLMTestCase(
        input="What is the 2+2",
        actual_output="4",
        expected_output="4",
        # HallucinationMetric needs grounding context against which the
        # actual_output is judged. Add a tiny factual context.
        context=["Basic arithmetic: 2 + 2 = 4."],
    )

    # Judge via OpenRouter instead of the default OpenAI fallback, whose key
    # is out of quota. Constructed explicitly (rather than passing a plain
    # model string) because deepeval snapshots its provider-routing settings
    # from the environment at pytest-plugin import time, before this file's
    # code runs — a USE_OPENROUTER_MODEL env var set here would be too late.
    judge = OpenRouterModel(
        model=JUDGE_MODEL_NAME,
        api_key=os.getenv("OPENROUTER_API_KEY"),
    )
    metric = [
        AnswerRelevancyMetric(threshold=0.8, model=judge),
        HallucinationMetric(threshold=0.1, model=judge),
    ]

    assert_test(test, metric)