# Define Your QA Team
# # Our task of BugTriageCrew is to prioritize, analyze, find RCA (root cause analysis)
# for these applications.
# In short -> Why bug occurs?

# # Sample bug report
# bug_report = """
# Bug Title: Shopping cart total shows $0.00 after applying discount code
# Bug ID: BUG-4521
# Reporter: manual_tester_jane
# Environment: Production, Chrome 120, Windows 11
# Severity (Reporter): High

# Steps to Reproduce:
# 1. Add 3+ items to shopping cart (total > $50)
# 2. Apply discount code "SAVE20" (20% off)
# 3. Observe the cart total

# Actual Result: Cart total shows $0.00 instead of discounted price
# Expected Result: Cart total should show original price minus 20%

# Additional Info:
# - Happens only when cart has 3+ items
# - Works fine with 1-2 items
# - Started after last Friday's deployment (v2.4.1)
# - No errors in browser console
# - API response shows correct discounted amount
# """

"""QA Bug Triage Agents — Each agent is a specialist."""

from crewai import Agent, Task, Crew, Process
from crewai import LLM
from dotenv import load_dotenv
import os
import requests

load_dotenv()


# Workaround: CrewAI 1.14.6 attaches a `cache_breakpoint` field to chat
# messages that Groq's OpenAI-compatible endpoint rejects. Strip it before
# every call.
class GroqLLM(LLM):
    def call(self, messages, *args, **kwargs):
        if isinstance(messages, list):
            cleaned = []
            for m in messages:
                if isinstance(m, dict):
                    m = {k: v for k, v in m.items() if k != "cache_breakpoint"}
                cleaned.append(m)
            messages = cleaned
        return super().call(messages, *args, **kwargs)


# Step 0 - Setup the Brain (GPT-OSS 120B via Groq)
groq_llm = GroqLLM(
    model="groq/openai/gpt-oss-120b",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_KEY"),
)


# Agent 1: Bug Triage Analyst
# Agent 2: Root Cause Investigator
# Agent 3: Test Recommendation Agent

# Task 1: Classify the bug
# Task 2: Investigate root cause (uses triage output as context)
# Task 3: Recommend tests (uses both previous outputs)


# How to fetch from the JIRA?
# JIRA API

def fetch_jira_ticket(bug_id):
    url = f"https://bugzzzzzz.atlassian.net/rest/api/3/issue/{bug_id}"
    r = requests.get(url, auth=(os.getenv("JIRA_EMAIL"), os.getenv("JIRA_API_TOKEN")))
    data = r.json()
    f = data["fields"]
    desc = f["description"]["content"][0]["content"][0]["text"]

    return f"""Bug Title: {f['summary']}
    Bug ID: {data['key']}
    Reporter: {f['reporter']['displayName']}

    {desc}"""


print(fetch_jira_ticket("AIT-2"))
bug_report = fetch_jira_ticket("AIT-2")
print(bug_report)

# Agent 1: Bug Triage Analyst
bug_analyst = Agent(
    role="Senior Bug Triage Analyst",
    goal="Accurately classify incoming bugs by severity, category, and priority",
    backstory="""You are a veteran QA engineer with 15 years of experience.
    You follow strict severity classification:
    - P0 (Blocker): System down, data loss, security breach
    - P1 (Critical): Major feature broken, no workaround
    - P2 (Major): Feature impaired, workaround exists
    - P3 (Minor): Cosmetic issue, minor inconvenience
    - P4 (Trivial): Enhancement request, typo
    You never inflate severity. You always justify your classification.""",
    llm=groq_llm,
    verbose=True,
    allow_delegation=False  # This agent handles its own work
)
# Agent 2: Root Cause Investigator
root_cause_agent = Agent(
    role="Root Cause Analysis Specialist",
    goal="Identify the likely root cause and affected system components",
    backstory="""You are a debugging expert who thinks in system layers.
    You analyze bugs by tracing through: UI → API → Service → Database.
    You identify whether the issue is in frontend, backend, 
    infrastructure, or third-party integration. You suggest which 
    log files or monitoring dashboards to check first.""",
    llm=groq_llm,
    verbose=True,
    allow_delegation=False
)
# Agent 3: Test Recommendation Agent
test_recommender = Agent(
    role="Test Strategy Advisor",
    goal="Recommend specific tests to validate the fix and prevent regression",
    backstory="""You are an SDET who designs test strategies.
    For every bug, you recommend:
    1. Immediate smoke tests to verify the fix
    2. Regression test cases to prevent recurrence
    3. Edge cases that should be added to the test suite
    You specify tests in Playwright TypeScript style when applicable.""",
    llm=groq_llm,
    verbose=True,
    allow_delegation=False
)

triage_task = Task(
    description=f"""Analyze and classify this bug report:

        {bug_report}

        Provide:
        1. Severity (P0-P4) with justification
        2. Category (UI, Functional, Performance, Security, Data)
        3. Affected component/module
        4. Business impact assessment
        5. Recommended priority for sprint planning""",

    expected_output="""A structured triage report with severity, 
        category, component, business impact, and sprint priority.""",
    agent=bug_analyst
)

# Task 2: Investigate root cause (uses triage output as context)
root_cause_task = Task(
    description=f"""Based on the triage analysis, investigate the 
    likely root cause of this bug:

    {bug_report}

        Provide:
        1. Most likely root cause
        2. System layer affected (UI/API/Service/DB/Infra)
        3. Related components that might be impacted
        4. Suggested investigation steps
        5. Which logs/dashboards to check first""",

    expected_output="""A root cause analysis report with the probable 
    cause, affected layer, related components, and investigation steps.""",
    agent=root_cause_agent,
    context=[triage_task]  # Receives output from triage
)

test_task = Task(
    description=f"""Based on the triage and root cause analysis, 
    recommend test cases for this bug:

    {bug_report}

        Provide:
        1. Verification test (confirm the fix works)
        2. 3-5 regression test cases
        3. Edge cases to add to the test suite
        4. Suggested test automation approach (Playwright with Typescript)
        5. Any load/performance tests if applicable""",

    expected_output="""A test recommendation report with verification 
    tests, regression cases, edge cases, and automation approach.""",
    agent=test_recommender,
    context=[triage_task, root_cause_task]  # Uses both outputs
)

crew = Crew(
    agents=[bug_analyst, root_cause_agent, test_recommender],
    tasks=[triage_task, root_cause_task, test_task],
    process=Process.sequential,
    verbose=True
)

print("🔍 QA Bug Triage Crew — Starting Analysis")
print("=" * 60)

result = crew.kickoff()
print("\n" + "=" * 60)
print("📋 FINAL TRIAGE REPORT")
print("=" * 60)
print(result)