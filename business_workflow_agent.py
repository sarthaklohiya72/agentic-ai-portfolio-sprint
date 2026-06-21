from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from typing import TypedDict
import pandas as pd
import datetime
import json
import uuid
import sys
import os

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

def write_audit_log(event, details):
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event": event,
        "details": details
    }
    with open("audit_log.json", "a") as f:
        f.write(json.dumps(entry) + "\n")

orders = pd.read_csv("orders.csv")
inventory = pd.read_csv("inventory.csv")
clients = pd.read_csv("clients.csv")

total_revenue = orders["order_value"].sum()
pending_orders = orders[orders["status"] == "pending"]
pending_value = pending_orders["order_value"].sum()
pending_count = len(pending_orders)
top_buyer = orders.groupby("buyer_name")["order_value"].sum().idxmax()
low_stock = inventory[inventory["current_stock"] < inventory["reorder_level"]]["product_name"].tolist()
overdue_clients = clients[clients["last_contact_date"] < "2026-03-01"]["client_name"].tolist()

today = datetime.date.today().strftime("%d %B %Y")

client_data = f"""
CLIENT A MANUFACTURING — WEEKLY DATA
Report Date: {today}

REVENUE:
Total revenue: ₹{total_revenue:,.0f}
Pending revenue at risk: ₹{pending_value:,.0f}
Pending orders count: {pending_count}

TOP BUYER: {top_buyer}

LOW STOCK PRODUCTS: {', '.join(low_stock)}

CLIENTS NOT CONTACTED RECENTLY:
{', '.join(overdue_clients) if overdue_clients else 'All clients contacted'}

PRODUCTION CONTEXT:
Factory: Client A Manufacturing, Sample City
Product: Metal Components
Capacity: 1,000 units/month
"""

class ReportState(TypedDict):
    data: str
    ops_analysis: str
    sales_analysis: str
    final_report: str
    missing_facts_flag: bool
    sensitive_flag: bool
    approved: bool

def ops_node(state: ReportState) -> ReportState:
    print("🔧 Operations Agent analyzing...")
    response = llm.invoke(f"""You are an operations analyst for Indian manufacturing.

Analyze this data and give 3 operational insights with actions:
{state['data']}

Keep under 120 words. Be specific with numbers.""")
    state["ops_analysis"] = response.content
    return state

def sales_node(state: ReportState) -> ReportState:
    print("💰 Sales Agent analyzing...")
    response = llm.invoke(f"""You are a sales analyst for B2B manufacturing in India.

Analyze this data and give 3 sales actions with expected revenue impact:
{state['data']}

Keep under 120 words. Be specific with client names and rupee amounts.""")
    state["sales_analysis"] = response.content
    return state

def report_node(state: ReportState) -> ReportState:
    print("📝 Report Agent writing executive summary...")
    response = llm.invoke(f"""You are an executive report writer for factory owners.

Operations Analysis:
{state['ops_analysis']}

Sales Analysis:
{state['sales_analysis']}

Write this exact format:

═══════════════════════════════════
CLIENT A MANUFACTURING
WEEKLY EXECUTIVE REPORT — {today}
═══════════════════════════════════

SITUATION (2 lines):

THIS WEEK'S TOP 3 ACTIONS:
1. [Action — Owner/Manager — By when]
2. [Action — Owner/Manager — By when]
3. [Action — Owner/Manager — By when]

REVENUE AT RISK: ₹__
ACTION TO RECOVER: __

NEXT WEEK FOCUS: __
═══════════════════════════════════

Keep under 200 words.""")
    state["final_report"] = response.content
    return state

def approval_node(state: ReportState) -> ReportState:
    print("\n🔎 Checking report before approval...")

    state["missing_facts_flag"] = (
        state["ops_analysis"].strip() == "" or
        state["sales_analysis"].strip() == ""
    )
    sensitive_keywords = ["₹", "Client", "buyer", "Buyer"]
    state["sensitive_flag"] = any(word in state["final_report"] for word in sensitive_keywords)

    print("\n--- DRAFT REPORT ---")
    print(state["final_report"])
    print("---------------------")
    print(f"Missing-facts flag: {state['missing_facts_flag']}")
    print(f"Sensitive-data flag: {state['sensitive_flag']}")

    answer = input("\nApprove this report for saving? (yes/no): ").strip().lower()
    state["approved"] = (answer == "yes")

    write_audit_log(
        event="approval_decision",
        details={
            "approved": state["approved"],
            "missing_facts_flag": state["missing_facts_flag"],
            "sensitive_flag": state["sensitive_flag"]
        }
    )
    return state

graph = StateGraph(ReportState)
graph.add_node("ops_agent", ops_node)
graph.add_node("sales_agent", sales_node)
graph.add_node("report_agent", report_node)
graph.add_node("approval_agent", approval_node)
graph.set_entry_point("ops_agent")
graph.add_edge("ops_agent", "sales_agent")
graph.add_edge("sales_agent", "report_agent")
graph.add_edge("report_agent", "approval_agent")
graph.add_edge("approval_agent", END)

print("\n" + "="*60)
print("CLIENT A MANUFACTURING — GOVERNED WEEKLY REPORT AGENT")
print("="*60 + "\n")

with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
    app = graph.compile(checkpointer=checkpointer, interrupt_before=["approval_agent"])

    if len(sys.argv) > 1 and sys.argv[1] == "--resume":
        thread_id = sys.argv[2]
        config = {"configurable": {"thread_id": thread_id}}
        print(f"▶️  Resuming thread {thread_id} ...\n")
        write_audit_log(event="run_resumed", details={"thread_id": thread_id})

        result = app.invoke(None, config=config)

        if result["approved"]:
            filename = f"weekly_report_{today.replace(' ', '_')}.txt"
            with open(filename, "w") as f:
                f.write(result["final_report"])
            print(f"\n✅ Report approved and saved to {filename}")
            write_audit_log(event="report_saved", details={"filename": filename, "thread_id": thread_id})
        else:
            print("\n🚫 Report was not approved — nothing was saved.")
            write_audit_log(event="report_rejected", details={"reason": "human declined approval", "thread_id": thread_id})

    else:
        thread_id = str(uuid.uuid4())[:8]
        config = {"configurable": {"thread_id": thread_id}}
        write_audit_log(event="run_started", details={"report_date": today, "thread_id": thread_id})

        app.invoke({
            "data": client_data,
            "ops_analysis": "",
            "sales_analysis": "",
            "final_report": "",
            "missing_facts_flag": False,
            "sensitive_flag": False,
            "approved": False
        }, config=config)

        print("\n⏸️  Paused before approval. State saved to checkpoints.sqlite.")
        print(f"👉 To resume: python business_workflow_agent.py --resume {thread_id}")
        write_audit_log(event="run_paused_before_approval", details={"thread_id": thread_id})