# Test Ananlyst Agent
#
# a senior QA with 15 years (JIRA MD)
#  of experience. Based on the feature,
# it will just analyze the requirement
#  and suggest a 5-10 testcases(p0 testcases).

from crewai import Agent, Task, Crew, Process
from crewai import LLM
from dotenv import load_dotenv
import os

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
    model="openai/openai/gpt-oss-120b",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_KEY"),
)

# Research and Writer Agent

researcher_agent = Agent(
        role="QA Research Analyst",
        goal = "Find the common bugs in the web application",
        backstory="You are a QA researcher who has analyzed " \
        "thousands of bug reports across web applications. " \
        "You specialize in identifying patterns and trends in software defects.",
        llm=groq_llm,
        verbose=True
)

writer_agent = Agent(
    role="QA Documentation Writer",
    goal="Create clear, actionable bug prevention guidelines",
    backstory="""You are a technical writer specializing in QA 
    documentation. You turn complex bug data into simple, 
    actionable checklists that developers can follow.""",
    llm=groq_llm,
    verbose=True
)

researcher_task = Task(
    description="""Research and list the top 5 most common bug 
    categories in modern web applications. For each category, 
    provide: name, frequency (percentage), example, and impact level.""",
    expected_output="""A ranked list of 5 bug categories with 
    name, frequency, example, and impact for each.""",
    agent=researcher_agent
)

writing_task = Task(
    description="""Based on the research provided, create a 
    'Bug Prevention Checklist' that developers can use before 
    submitting a pull request. Make it practical and actionable.""",
    expected_output="""A formatted checklist with 5-10 items 
    that developers can quickly review before code submission.""",
    agent=writer_agent
)


crew = Crew(
    agents= [researcher_agent,writer_agent],
    tasks=[researcher_task,writing_task],
    process=Process.sequential,
    verbose=True
)

result = crew.kickoff()
print(result)