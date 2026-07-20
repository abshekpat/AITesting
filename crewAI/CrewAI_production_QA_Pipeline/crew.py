"""
CrewAI + Jira MCP: Auto-Generate Test Plans, Test Cases & Playwright Scripts
─────────────────────────────────────────────────────────────────────────────
Input  : A Jira ticket ID (e.g., VWO-48)
Output :
  output/test_plan.md                        — 12-section test plan
  output/test_cases.md                       — detailed test cases (markdown table)
  output/test_cases_jira.csv                 — same test cases, Jira CSV-import ready
  output/advanced-playwright-framework/      — Playwright automation, scaffolded per
                                                docs/ARCHITECTURE.html and filled in
                                                by the Playwright Coder agent

Pipeline:
  1. Jira Analyst       → fetches ticket via MCP, extracts requirements
  2. Test Plan Writer   → writes complete test plan (12 sections), from templates/testplan.md
  3. Test Case Writer   → writes detailed test cases table (converted to Jira CSV afterwards)
  4. Playwright Coder   → generates one file per framework layer (pages/modules/tests/api/fixtures)
"""
import os
import copy
import csv
import datetime
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from crewai import Agent, Task, Crew, Process, LLM
from crewai_tools import MCPServerAdapter
from dotenv import load_dotenv
import requests
from mcp import StdioServerParameters


load_dotenv()

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
FRAMEWORK_TEMPLATE_DIR = TEMPLATES_DIR / "playwright-framework"
FRAMEWORK_LAYERS = ("pages", "modules", "tests", "api", "fixtures", "testdata")


def _relax_strict_schema(schema):
    """Mark only defaultless params required, recursively.

    CrewAI emits OpenAI strict-mode tool schemas: every property is forced into
    `required` and `strict: True` is set. OpenAI constrains decoding to satisfy
    that, so omitting an optional arg is impossible. Groq doesn't — it validates
    the model's tool call against the schema and rejects it outright when
    optional args are missing ("parameters for tool X did not match schema").
    A param carrying a `default` is optional, so keep it out of `required`.
    """
    if not isinstance(schema, dict):
        return schema
    properties = schema.get("properties")
    if schema.get("type") == "object" and isinstance(properties, dict):
        schema["required"] = [
            name
            for name, spec in properties.items()
            if not (isinstance(spec, dict) and "default" in spec)
        ]
    for value in schema.values():
        if isinstance(value, dict):
            _relax_strict_schema(value)
        elif isinstance(value, list):
            for item in value:
                _relax_strict_schema(item)
    return schema


# Workaround: CrewAI 1.14.6 attaches a `cache_breakpoint` field to chat
# messages that Groq's OpenAI-compatible endpoint rejects. Strip it before
# every call. Groq also rejects CrewAI's strict-mode tool schemas, so relax
# those too.
class GroqLLM(LLM):
    def call(self, messages, tools=None, *args, **kwargs):
        if isinstance(messages, list):
            cleaned = []
            for m in messages:
                if isinstance(m, dict):
                    m = {k: v for k, v in m.items() if k != "cache_breakpoint"}
                cleaned.append(m)
            messages = cleaned
        if tools:
            relaxed = []
            for t in tools:
                t = copy.deepcopy(t)
                fn = t.get("function") if isinstance(t, dict) else None
                if isinstance(fn, dict):
                    fn.pop("strict", None)
                    _relax_strict_schema(fn.get("parameters"))
                relaxed.append(t)
            tools = relaxed
        return super().call(messages, tools, *args, **kwargs)

# Step 0 - Setup the Brain.
# gpt-oss-120b free tier on Groq caps at 8000 TPM, which this 4-task pipeline
# (with accumulated context) blows past. llama-3.3-70b-versatile sits at 30k
# TPM on the same tier — plenty for the full crew. Swap back if you upgrade.
groq_llm = GroqLLM(
    model="groq/llama-3.3-70b-versatile",
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_KEY"),
)

# ══════════════════════════════════════════════════════════════════
#  MCP SERVER CONFIGURATION
# ══════════════════════════════════════════════════════════════════

def get_mcp_server_params() -> StdioServerParameters:
    """
    Configure the mcp-atlassian server connection.

    This tells CrewAI to launch `uvx mcp-atlassian` as a subprocess
    and communicate with it over STDIO (stdin/stdout).

    The MCP server handles:
    - Jira REST API authentication
    - ADF (Atlassian Document Format) → text conversion
    - Pagination for large result sets
    - Error handling and retries
    """
    # Accept either JIRA_USERNAME or JIRA_EMAIL (Atlassian Cloud uses email
    # as the username). Default JIRA_URL to the known workspace if missing.
    jira_username = os.getenv("JIRA_USERNAME") or os.getenv("JIRA_EMAIL", "")
    jira_url = os.getenv("JIRA_URL")
    return StdioServerParameters(
        command="uvx",
        args=["mcp-atlassian"],
        env={
            # Pass Jira credentials to the MCP server process
            "JIRA_URL": jira_url,
            "JIRA_USERNAME": jira_username,
            "JIRA_API_TOKEN": os.getenv("JIRA_API_TOKEN", ""),
            # Inherit PATH so `uvx` can find Python/Node
            "PATH": os.environ.get("PATH", ""),
            # Pin python for the uvx-spawned tool
            "UV_PYTHON": "3.12",
        },
    )

# ══════════════════════════════════════════════════════════════════
#  TEST PLAN TEMPLATE — pulled from templates/testplan.md so the template
#  can be edited without touching this file.
# ══════════════════════════════════════════════════════════════════

TEST_PLAN_TEMPLATE = (TEMPLATES_DIR / "testplan.md").read_text()


# ══════════════════════════════════════════════════════════════════
#  AGENTS
# ══════════════════════════════════════════════════════════════════

def create_agents(mcp_tools: list, ticket_id: str):
    """Create all four agents with MCP tools and return them."""

    # ── Agent 1: Jira Ticket Analyst ──────────────────────────────
    jira_analyst = Agent(
        role="Senior QA Analyst",
        goal=(
            f"Fetch Jira ticket {ticket_id} using the available Jira tools, "
            "then extract ALL testable requirements, acceptance criteria, "
            "edge cases, and risks."
        ),
        backstory=(
            "You are a senior QA analyst with 15+ years of experience. "
            "You have access to Jira through MCP tools. "
            "Your job is to fetch the ticket details and perform "
            "a thorough analysis of what needs to be tested. "
            "You identify functional requirements, acceptance criteria, "
            "edge cases, boundary conditions, and risks. "
            "IMPORTANT: Use the Jira tools to fetch the ticket first, "
            "then analyze what you receive."
        ),
        tools=mcp_tools,  # ← MCP tools injected here!
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )
    # ── Agent 2: Test Plan Writer ─────────────────────────────────
    test_plan_writer = Agent(
        role="Test Plan Documentation Specialist",
        goal=(
            "Create a comprehensive, professional test plan document "
            "following the standard 12-section template."
        ),
        backstory=(
            f"You are a certified ISTQB test planning expert. "
            f"You write detailed test plans that teams can immediately execute. "
            f"You MUST follow this template:\n{TEST_PLAN_TEMPLATE}\n"
            f"Today's date is {datetime.date.today().strftime('%B %d, %Y')}. "
            f"Use professional markdown formatting."
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )
    # ── Agent 3: Test Case Writer ─────────────────────────────────
    test_case_writer = Agent(
        role="Test Case Design Specialist",
        goal=(
            "Design detailed, executable test cases covering positive, "
            "negative, edge, and boundary scenarios."
        ),
        backstory=(
            "You are a QA engineer who specializes in test case design. "
            "You write test cases that are so clear and detailed that "
            "anyone — even a junior tester — can execute them without "
            "asking questions. Each test case includes: TC ID, Title, "
            "Preconditions, Step-by-step instructions, Expected Results, "
            "Test Data, and Priority. You always cover: "
            "happy path, negative scenarios, edge cases, boundary values, "
            "UI validations, and error handling."
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    # ── Agent 4: Playwright Script Generator ──────────────────────
    playwright_coder = Agent(
        role="Playwright Automation Engineer",
        goal=(
            "Generate production-ready Playwright TypeScript files that "
            "slot directly into the team's Advanced Playwright Framework "
            "(Page Object Model + Module pattern), one file per "
            "<<<FILE>>> block."
        ),
        backstory=(
            "You are a senior SDET and maintainer of the team's Advanced "
            "Playwright Framework (Page Object Model + Module pattern, see "
            "docs/ARCHITECTURE.html). You never put a locator inside a "
            "module, never put business logic inside a page class, and you "
            "always tag and test.step() your specs. Proper locator "
            "strategy is data-testid > CSS > XPath. You generate COMPLETE, "
            "RUNNABLE TypeScript files, laid out exactly per the "
            "framework's layers, and you emit them using the <<<FILE>>> "
            "block format so a script can write them straight into the "
            "project — never as a single markdown blob."
        ),
        llm=groq_llm,
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    return jira_analyst, test_plan_writer, test_case_writer, playwright_coder

# ══════════════════════════════════════════════════════════════════
#  TASKS
# ══════════════════════════════════════════════════════════════════

def create_tasks(agents: tuple, ticket_id: str):
    """Create all four tasks and wire them together.

    None of the tasks use CrewAI's `output_file` — its path validator
    silently strips a leading '/' from absolute paths (turning them into
    CWD-relative paths), which breaks callers whose CWD isn't the pipeline
    directory, like the /ui app. Instead run_crew() writes every artifact
    itself from `task.output.raw` into the caller-supplied output_dir.
    """

    jira_analyst, test_plan_writer, test_case_writer, playwright_coder = agents

    # ── Task 1: Fetch & Analyze Jira Ticket ───────────────────────
    analysis_task = Task(
        description=(
            f"Fetch Jira ticket **{ticket_id}** using the available Jira MCP tools.\n\n"
            "Look for a tool that can get issue details — it might be called "
            "something like 'jira_get_issue' or 'get_issue' or similar.\n\n"
            f"Pass the ticket ID '{ticket_id}' to fetch the full details.\n\n"
            "After fetching, provide a DETAILED analysis:\n"
            "1. Summary of the ticket (what the feature/bug is about)\n"
            "2. ALL testable requirements extracted from the ticket\n"
            "3. Acceptance criteria (explicit and implicit)\n"
            "4. Potential edge cases and boundary conditions\n"
            "5. Risks and dependencies\n"
            "6. Suggested testing types (functional, regression, performance, etc.)\n\n"
            "Be thorough — all other agents depend on your analysis."
        ),
        expected_output=(
            "A detailed analysis report containing: ticket summary, "
            "testable requirements list, acceptance criteria, edge cases, "
            "risks, and recommended testing types."
        ),
        agent=jira_analyst,
    )

    # ── Task 2: Write Test Plan ───────────────────────────────────
    test_plan_task = Task(
        description=(
            f"Based on the Jira ticket analysis, create a COMPLETE test plan "
            f"for {ticket_id}.\n\n"
            "Follow the standard 12-section template EXACTLY. Include:\n"
            "- All 12 sections from the template\n"
            "- High-level test scenarios (NOT detailed test cases)\n"
            "- Realistic risk assessment with 3-5 risks\n"
            "- Proper test schedule with phases\n"
            f"- Use today's date: {datetime.date.today().strftime('%B %d, %Y')}\n\n"
            "Format everything in clean, professional markdown."
        ),
        expected_output=(
            "A complete, professional test plan document in markdown format "
            "following all 12 sections of the template."
        ),
        agent=test_plan_writer,
        context=[analysis_task],
    )
    # ── Task 3: Write Detailed Test Cases ─────────────────────────
    test_cases_task = Task(
        description=(
            f"Based on the ticket analysis and test plan, create DETAILED "
            f"test cases for {ticket_id}.\n\n"
            "Generate at least 12-15 test cases in a markdown table:\n\n"
            "| TC ID | Title | Preconditions | Steps | Expected Result | "
            "Test Data | Priority |\n\n"
            "Cover these categories:\n"
            "- Happy path / positive scenarios (3-4 cases)\n"
            "- Negative scenarios / invalid inputs (3-4 cases)\n"
            "- Edge cases / boundary values (2-3 cases)\n"
            "- UI/UX validations (2-3 cases)\n"
            "- API validations if applicable (1-2 cases)\n"
            "- Performance/load considerations (1 case)\n\n"
            "Each test case MUST have:\n"
            "- Clear, numbered step-by-step instructions\n"
            "- Specific test data (not generic)\n"
            "- Precise expected results\n"
            "- Priority: P0 (Blocker), P1 (Critical), P2 (Major), P3 (Minor)"
        ),
        expected_output=(
            "A markdown document with 12-15 detailed test cases in table "
            "format, covering positive, negative, edge, UI, and API scenarios."
        ),
        agent=test_case_writer,
        context=[analysis_task, test_plan_task],
    )

    # ── Task 4: Generate Playwright Scripts ───────────────────────
    playwright_task = Task(
        description=(
            f"Generate the Playwright automation code for {ticket_id}, "
            "based on the test cases above. Your code will be dropped "
            "directly into an existing 'Advanced Playwright Framework' "
            "project (Page Object Model + Module pattern) that ALREADY "
            "has playwright.config.ts, tsconfig.json, and "
            "src/utils/{Logger,WaitHelper,DataGenerator,ApiHelper}.ts and "
            "src/config/index.ts in place. Do NOT recreate that "
            "boilerplate — only produce the feature-specific files below.\n\n"
            "STRICT LAYER RULES (this is a code-reviewed framework; "
            "violations get rejected):\n"
            "- src/pages/*.ts — Page classes: locators as arrow functions "
            "plus thin UI-action methods ONLY. No if/else, no assertions, "
            "no business logic.\n"
            "- src/modules/*.ts — Module classes: business-logic "
            "orchestration on top of Page classes. NEVER call "
            "`this.page.locator(...)` directly in a module — always go "
            "through a Page class method.\n"
            "- src/tests/*.spec.ts — test.describe()/test() specs. Import "
            "`test`/`expect` from '@fixtures', NOT from '@playwright/test' "
            "directly. Tag every describe block (e.g. '@P0 Login', "
            "'@P1 Checkout'). Wrap each logical action in "
            "`await test.step(...)`. Include beforeEach/afterEach where "
            "useful.\n"
            "- src/fixtures/index.ts — EXACTLY ONE file. Extend the base "
            "`test`/`expect` from '@playwright/test' with `test.extend<>` "
            "so specs can destructure page/module fixtures directly (e.g. "
            "`{ loginModule }`). It MUST follow this exact shape (adapt "
            "names to your pages/modules, keep the structure):\n"
            "  import { test as base, expect } from '@playwright/test';\n"
            "  import { LoginPage } from '@pages/LoginPage';\n"
            "  import { LoginModule } from '@modules/LoginModule';\n"
            "  type Fixtures = { loginPage: LoginPage; loginModule: LoginModule };\n"
            "  export const test = base.extend<Fixtures>({\n"
            "    loginPage: async ({ page }, use) => { await use(new LoginPage(page)); },\n"
            "    loginModule: async ({ page, loginPage }, use) => {\n"
            "      await use(new LoginModule(page, loginPage));\n"
            "    },\n"
            "  });\n"
            "  export { expect };\n"
            "- src/api/*.ts — only if the ticket involves API behavior: "
            "thin API client classes built on `ApiHelper` from "
            "'@utils/ApiHelper'.\n\n"
            "EVERY class/interface/type declared at the top level of a "
            "pages/modules/api file MUST start with the `export` keyword "
            "(e.g. `export class LoginPage { ... }`), never a bare `class "
            "LoginPage { ... }` — fixtures/index.ts imports them by name "
            "and an unexported class fails to compile.\n\n"
            "Import shared infra with these path aliases (already "
            "configured in tsconfig.json): '@fixtures', '@pages/X', "
            "'@modules/X', '@utils/X', '@api/X', '@config'.\n\n"
            "OUTPUT FORMAT — this is parsed by a script, follow it "
            "exactly. For every file, emit a block:\n"
            "<<<FILE: pages/LoginPage.ts>>>\n"
            "...raw TypeScript, no markdown code fences...\n"
            "<<<END FILE>>>\n\n"
            "Rules:\n"
            "- Path is relative to src/, forward slashes, no leading "
            "slash, no '..'.\n"
            "- Only use these top-level folders: pages/, modules/, "
            "tests/, api/, fixtures/, testdata/.\n"
            "- Do NOT wrap file contents in ``` fences.\n"
            "- Do NOT emit any text outside <<<FILE>>>...<<<END FILE>>> "
            "blocks.\n"
            "- Generate COMPLETE, RUNNABLE code — no placeholders or "
            "TODOs."
        ),
        expected_output=(
            "A sequence of <<<FILE: ...>>> ... <<<END FILE>>> blocks "
            "containing complete TypeScript source for the pages, "
            "modules, one fixtures/index.ts, test specs, and (if "
            "applicable) api clients needed to automate the test cases — "
            "nothing else in the response."
        ),
        agent=playwright_coder,
        context=[analysis_task, test_cases_task],
    )

    return analysis_task, test_plan_task, test_cases_task, playwright_task

# ══════════════════════════════════════════════════════════════════
#  POST-PROCESSING: Jira CSV export + Advanced Playwright Framework files
# ══════════════════════════════════════════════════════════════════

# Matches the <<<FILE: path>>> ... <<<END FILE>>> blocks the Playwright
# Coder agent is instructed to emit (see Task 4's description).
FILE_BLOCK_RE = re.compile(
    r"<<<FILE:\s*(?P<path>[^\n>]+?)\s*>>>\r?\n(?P<content>.*?)(?:\r?\n)?<<<END FILE>>>",
    re.DOTALL,
)


def scaffold_playwright_framework(output_root: Path) -> Path:
    """Copy the static framework skeleton (config + shared utils) into
    output/advanced-playwright-framework/, matching docs/ARCHITECTURE.html.

    Agent 4 only ever writes into src/{pages,modules,tests,api,fixtures,
    testdata} — everything else here (playwright.config.ts, tsconfig.json,
    package.json, src/config, src/utils) is shared infrastructure that
    ships with the framework, not something the LLM regenerates each run.
    """
    framework_dir = output_root / "advanced-playwright-framework"
    shutil.copytree(FRAMEWORK_TEMPLATE_DIR, framework_dir, dirs_exist_ok=True)
    for layer in FRAMEWORK_LAYERS:
        (framework_dir / "src" / layer).mkdir(parents=True, exist_ok=True)
    return framework_dir


def write_playwright_files(raw_output: str, framework_dir: Path) -> list[Path]:
    """Split the Playwright Coder agent's <<<FILE: ...>>> blocks and write
    each one into its layer folder under framework_dir/src/.

    Any block whose path escapes the approved layer folders is skipped —
    this keeps the LLM from writing outside the framework's architecture.
    """
    written: list[Path] = []
    for match in FILE_BLOCK_RE.finditer(raw_output):
        rel_path = match.group("path").strip().lstrip("/")
        if rel_path.startswith("src/"):
            rel_path = rel_path[len("src/"):]
        parts = PurePosixPath(rel_path).parts
        if not parts or parts[0] not in FRAMEWORK_LAYERS or ".." in parts:
            continue

        content = match.group("content").strip("\n")
        # Defensive: strip a wrapping ```lang fence if the model added one anyway.
        content = re.sub(r"^```[a-zA-Z]*\n", "", content)
        content = re.sub(r"\n```$", "", content)
        # Defensive: the framework requires named exports (see
        # ARCHITECTURE.html's review checklist), but the model sometimes
        # drops `export` on a top-level class/interface. Without it,
        # fixtures/index.ts's `import { X } from '@pages/X'` fails to
        # compile, so patch it in rather than trust every generation.
        content = re.sub(
            r"(?m)^(class|interface|type)\s", r"export \1 ", content
        )

        target = framework_dir / "src" / Path(*parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.rstrip() + "\n")
        written.append(target)
    return written


def write_jira_csv(test_cases_markdown: str, csv_path: Path) -> int:
    """Convert the Test Case Writer's markdown table into a CSV that Jira's
    native importer can map column-by-column (Preconditions/Steps/Test
    Data/Expected Result land as custom fields during the import wizard).

    Returns the number of test cases written.
    """
    header = (
        (TEMPLATES_DIR / "jira_test_cases_header.csv")
        .read_text()
        .strip()
        .split(",")
    )
    priority_map = {"P0": "Highest", "P1": "High", "P2": "Medium", "P3": "Low"}

    rows = []
    for line in test_cases_markdown.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        # Skip markdown separator rows like |---|---|---|
        if set(line.replace("|", "").strip()) <= {"-", " ", ":"}:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7 or cells[0].lower() in ("tc id", "id"):
            continue

        tc_id, title, preconditions, steps, expected, test_data, priority = cells[:7]
        jira_priority = priority_map.get(priority.upper(), priority or "Medium")
        description = (
            f"Preconditions: {preconditions}\n\n"
            f"Steps:\n{steps}\n\n"
            f"Expected Result: {expected}\n\n"
            f"Test Data: {test_data}"
        )
        rows.append(
            [
                "Test",
                f"[{tc_id}] {title}",
                jira_priority,
                priority.upper(),
                description,
                preconditions,
                steps,
                test_data,
                expected,
            ]
        )

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    return len(rows)


# ══════════════════════════════════════════════════════════════════
#  CREW ORCHESTRATION
# ══════════════════════════════════════════════════════════════════

@dataclass
class PipelineResult:
    """Everything a caller (CLI or the /ui app) needs to point at what a
    run produced, without re-deriving paths from ticket_id itself."""

    ticket_id: str
    output_dir: Path
    test_plan_path: Path
    test_cases_path: Path
    jira_csv_path: Path
    jira_csv_count: int
    framework_dir: Path
    framework_files: list[Path] = field(default_factory=list)
    crew_output: object = None


def run_crew(ticket_id: str, output_dir: str | Path = "output") -> PipelineResult:
    """
    Main function: Connect to Jira MCP → Create Crew → Run Pipeline.

    The MCPServerAdapter handles:
    1. Launching `uvx mcp-atlassian` as a subprocess
    2. Discovering all available Jira tools via MCP protocol
    3. Converting MCP tools to CrewAI-compatible BaseTool instances
    4. Cleaning up the subprocess when done (context manager)

    output_dir defaults to "output" for the single-ticket CLI (main.py).
    Callers running several tickets in one process (the /ui app) should
    pass a distinct directory per ticket_id so runs don't overwrite each
    other's test_plan.md/test_cases.md/framework files.
    """
    print(f"\n📡 Target Jira Ticket: {ticket_id}")
    print("=" * 60)

    # Create output directory + scaffold the Advanced Playwright Framework
    # (config, tsconfig, package.json, shared utils) so Agent 4 only ever
    # has to add pages/modules/tests/api/fixtures into an existing project.
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    framework_dir = scaffold_playwright_framework(output_dir)

    # ── Connect to Jira MCP Server ────────────────────────────────
    server_params = get_mcp_server_params()

    print("🔌 Connecting to Jira MCP server (mcp-atlassian)...")

    with MCPServerAdapter(server_params, connect_timeout=60) as mcp_tools:
        # Show discovered tools
        tool_names = [t.name for t in mcp_tools]
        print(f"✅ Connected! Discovered {len(mcp_tools)} Jira tools:")
        for name in tool_names:
            print(f"   • {name}")
        print()

        # Groq free tier caps `gpt-oss-120b` at 8000 TPM. mcp-atlassian
        # exposes ~49 tools — every tool schema is added to the system
        # prompt and easily blows the budget. Filter to just what Agent 1
        # actually needs: read a Jira issue.
        ALLOWED = {"jira_get_issue", "jira_search"}
        filtered_tools = [t for t in mcp_tools if t.name in ALLOWED]
        print(f"🔧 Using {len(filtered_tools)} tool(s) to stay under TPM limit: "
              f"{[t.name for t in filtered_tools]}\n")

        # ── Create Agents (inject MCP tools into Agent 1) ─────────
        agents = create_agents(filtered_tools, ticket_id)

        # ── Create Tasks (wired sequentially) ─────────────────────
        tasks = create_tasks(agents, ticket_id)
        analysis_task, test_plan_task, test_cases_task, playwright_task = tasks

        # ── Assemble the Crew ─────────────────────────────────────
        crew = Crew(
            agents=list(agents),
            tasks=list(tasks),
            process=Process.sequential,
            verbose=True,
            max_rpm=4,  # Rate limit for Groq free tier
        )

        # ── Run! ──────────────────────────────────────────────────
        print(f"\n🚀 Starting QA Pipeline for {ticket_id}")
        print("=" * 60)

        result = crew.kickoff()

        # ── Post-process: write test_plan.md / test_cases.md ourselves.
        # (Not via CrewAI's output_file — see create_tasks()'s docstring.)
        (output_dir / "test_plan.md").write_text(test_plan_task.output.raw)
        (output_dir / "test_cases.md").write_text(test_cases_task.output.raw)

        # ── Post-process: Jira CSV export ──────────────────────────
        csv_count = write_jira_csv(
            test_cases_task.output.raw, output_dir / "test_cases_jira.csv"
        )

        # ── Post-process: split Agent 4's output into framework files ──
        written_files = write_playwright_files(playwright_task.output.raw, framework_dir)
        # Keep the raw agent output for troubleshooting bad/unparsed blocks.
        (framework_dir / "GENERATION_LOG.md").write_text(playwright_task.output.raw)

        print("\n" + "=" * 60)
        print("🎉 QA PIPELINE COMPLETE!")
        print("=" * 60)
        print(f"\n📁 Generated files in ./{output_dir}/:")
        print(f"   📋 test_plan.md            — Complete test plan")
        print(f"   🧪 test_cases.md           — Detailed test cases")
        print(f"   🧾 test_cases_jira.csv     — {csv_count} test case(s), Jira CSV-import ready")
        print(f"   🎭 advanced-playwright-framework/ — {len(written_files)} file(s) added to the framework")
        for f in written_files:
            print(f"      • {f.relative_to(output_dir)}")
        if not written_files:
            print("      ⚠️  No <<<FILE>>> blocks parsed — see GENERATION_LOG.md")
        print()

        return PipelineResult(
            ticket_id=ticket_id,
            output_dir=output_dir,
            test_plan_path=output_dir / "test_plan.md",
            test_cases_path=output_dir / "test_cases.md",
            jira_csv_path=output_dir / "test_cases_jira.csv",
            jira_csv_count=csv_count,
            framework_dir=framework_dir,
            framework_files=written_files,
            crew_output=result,
        )