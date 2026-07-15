from crewai import Agent, Task, Crew
from crewai import LLM
from dotenv import load_dotenv
import os

load_dotenv()

# Groq's OpenAI-compatible API rejects the prompt-cache marker CrewAI attaches
# to system/user messages. Strip it before messages reach the provider.
from crewai.llms.cache import CACHE_BREAKPOINT_KEY

_orig_format = LLM._format_messages_for_provider


def _strip_cache_breakpoint(self, messages):
    formatted = _orig_format(self, messages)
    return [
        {k: v for k, v in msg.items() if k != CACHE_BREAKPOINT_KEY}
        for msg in formatted
    ]


LLM._format_messages_for_provider = _strip_cache_breakpoint

# Step 0 - Set up the Brain
groq_llm = LLM(
    model="groq/openai/gpt-oss-120b",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_KEY"),
)

# Step 1 - Define the Agent (identity)
qa_agent = Agent(
    role="QA Engineer",
    goal="Analyse the feature and the requirements, and create 5-10 test cases out of it.",
    backstory="You are a senior QA engineer with 15 years of experience in test planning and testcases creation",
    llm=groq_llm,
    verbose=True
)

# Step 2 - Give the Task to the Agent
test_case_task = Task(
    description="Create 5-10 test cases",
    expected_output="A numbered list of 5-10 test cases with brief descriptions for a app.vwo.com Login page with the username, password and submit button with remember me functionality",
    agent=qa_agent
)

# 3. Add them to the Crew
crew = Crew(
    agents=[qa_agent],
    tasks=[test_case_task],
    verbose=True
)

result = crew.kickoff()
print(result)


