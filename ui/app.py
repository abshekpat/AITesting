"""Lightweight Streamlit UI for the CrewAI QA pipeline.

Run with (from the repo root, inside the project venv):

    streamlit run ui/app.py

Enter one or more Jira ticket IDs (comma- or newline-separated). The
pipeline in crewAI/CrewAI_production_QA_Pipeline/crew.py runs once per
ticket, writing test_plan.md, test_cases.md, test_cases_jira.csv and the
advanced-playwright-framework/ tree into a per-ticket output folder under
crewAI/CrewAI_production_QA_Pipeline/output/<ticket_id>/. This app just
drives that pipeline and displays what it produced — it holds no pipeline
logic of its own.
"""
import csv
import io
import re
import shutil
import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_DIR = REPO_ROOT / "crewAI" / "CrewAI_production_QA_Pipeline"
OUTPUT_ROOT = PIPELINE_DIR / "output"

sys.path.insert(0, str(PIPELINE_DIR))
import crew  # noqa: E402  (needs sys.path set up first)


st.set_page_config(page_title="CrewAI QA Pipeline", page_icon="🎭", layout="wide")
st.title("🎭 CrewAI QA Pipeline")
st.caption(
    "Fetch Jira tickets, generate a test plan, Jira-importable test cases, "
    "and Playwright automation laid out in the Advanced Playwright "
    "Framework structure."
)

raw_ids = st.text_area(
    "Jira ticket IDs",
    placeholder="AIT-2, AIT-5\nVWO-48",
    help="Comma or newline separated. Each ticket runs independently and "
    "gets its own output folder.",
    height=100,
)
run_clicked = st.button("Run pipeline", type="primary")


def folder_name_for(ticket_id: str) -> str:
    """Jira IDs are normally filesystem-safe (e.g. AIT-2), but sanitize
    defensively since this becomes a directory name."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", ticket_id)


def render_tree(root: Path, prefix: str = "") -> list[str]:
    lines = []
    entries = sorted(root.iterdir(), key=lambda p: (p.is_file(), p.name))
    for i, entry in enumerate(entries):
        connector = "└── " if i == len(entries) - 1 else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")
        if entry.is_dir():
            extension = "    " if i == len(entries) - 1 else "│   "
            lines.extend(render_tree(entry, prefix + extension))
    return lines


def show_result(result: "crew.PipelineResult") -> None:
    st.subheader(f"📁 {result.ticket_id}")

    tree_lines = [f"{result.output_dir.name}/"] + render_tree(result.output_dir)
    st.code("\n".join(tree_lines), language="text")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Test Plan (`test_plan.md`)**")
        test_plan_text = result.test_plan_path.read_text()
        st.download_button(
            "Download test_plan.md",
            test_plan_text,
            file_name=f"{result.ticket_id}_test_plan.md",
            key=f"plan-{result.ticket_id}",
        )
        with st.expander("Preview"):
            st.markdown(test_plan_text)

    with col2:
        st.markdown("**Test Cases (`test_cases.md`)**")
        test_cases_text = result.test_cases_path.read_text()
        st.download_button(
            "Download test_cases.md",
            test_cases_text,
            file_name=f"{result.ticket_id}_test_cases.md",
            key=f"cases-{result.ticket_id}",
        )
        with st.expander("Preview"):
            st.markdown(test_cases_text)

    st.markdown(f"**Jira CSV (`test_cases_jira.csv`)** — {result.jira_csv_count} test case(s)")
    csv_text = result.jira_csv_path.read_text()
    st.download_button(
        "Download test_cases_jira.csv",
        csv_text,
        file_name=f"{result.ticket_id}_test_cases_jira.csv",
        mime="text/csv",
        key=f"csv-{result.ticket_id}",
    )
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if rows:
        st.dataframe(rows, use_container_width=True)

    st.markdown(
        f"**Advanced Playwright Framework** — "
        f"{len(result.framework_files)} generated file(s) "
        f"(full scaffold at `{result.framework_dir.relative_to(result.output_dir)}/`)"
    )
    for f in result.framework_files:
        with st.expander(str(f.relative_to(result.framework_dir))):
            st.code(f.read_text(), language="typescript")

    zip_path = Path(shutil.make_archive(str(result.output_dir), "zip", result.output_dir))
    st.download_button(
        "Download everything (.zip)",
        zip_path.read_bytes(),
        file_name=f"{result.ticket_id}.zip",
        mime="application/zip",
        key=f"zip-{result.ticket_id}",
    )


if run_clicked:
    ticket_ids = [t.strip() for t in re.split(r"[,\n]", raw_ids) if t.strip()]
    ticket_ids = list(dict.fromkeys(ticket_ids))  # de-dupe, keep entry order

    if not ticket_ids:
        st.warning("Enter at least one Jira ticket ID.")

    for ticket_id in ticket_ids:
        ticket_output_dir = OUTPUT_ROOT / folder_name_for(ticket_id)
        with st.spinner(f"Running pipeline for {ticket_id}… this calls Jira + the LLM, expect ~1-2 min."):
            try:
                result = crew.run_crew(ticket_id, output_dir=ticket_output_dir)
            except Exception as exc:  # noqa: BLE001 — surface any failure per-ticket, keep going
                st.error(f"{ticket_id} failed: {exc}")
                continue
        st.success(f"{ticket_id} complete")
        show_result(result)
        st.divider()