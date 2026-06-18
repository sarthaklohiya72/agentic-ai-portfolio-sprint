# Business Workflow Agent

A LangGraph-based AI agent that reads raw client notes and turns them into a structured, human-approved action draft — built as a governed, human-in-the-loop workflow rather than a fully autonomous one.

## What it does
- Takes a plain-text note (e.g. a client update, stock alert, or request)
- Extracts the key facts and drafts a response or action plan
- Flags anything sensitive or missing key information
- Pauses for human approval before anything is finalized
- Logs every run to an audit trail

## Built with
- Python 3.12
- LangGraph (state, nodes, checkpoints)
- Groq API (llama-3.3-70b-versatile)

## How to run it
```bash
python business_workflow_agent.py --notes sample_client_notes.txt
```

## Status
Day 1 of a 45-day build sprint. Currently a single governed agent. Human-approval gate and audit logging are being added next.

## Note on data
All sample data in this repo is fictional / anonymized. No real client information is included.
