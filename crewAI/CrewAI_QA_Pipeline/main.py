"""
Entry point for the CrewAI + Jira MCP QA Pipeline.
Usage: python main.py VWO-48
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from crew import run_crew

if __name__ == "__main__":
    # Get ticket ID from command line or use default
    ticket_id = sys.argv[1] if len(sys.argv) > 1 else "AIT-2"
    run_crew(ticket_id)