from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import pandas as pd
import datetime
import os

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY")
)

# ── Load Data ──────────────────────────────────────
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

agrawal_data = f"""
AGRAWAL METAL WORKS — WEEKLY DATA
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
Factory: Agrawal Metal Works, Bhiwadi
Product: Copper and Brass
Capacity: 3,300 tons/month
"""

# ── State ──────────────────────────────────────────
from typing import TypedDict

class ReportState(TypedDict):
    data: str
    ops_analysis: str
    sales_analysis: str
    final_report: str

# ── Nodes ──────────────────────────────────────────
def ops_node(state: ReportState) -> ReportState:
    print("🔧 Operations Agent analyzing...")
    response = llm.invoke(f"""You are an operations analyst for Indian metal manufacturing.
    
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
    response = llm.invoke(f"""You are an executive report writer for factory owners in Rajasthan.

Operations Analysis:
{state['ops_analysis']}

Sales Analysis:
{state['sales_analysis']}

Write this exact format:

═══════════════════════════════════
AGRAWAL METAL WORKS
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

# ── Build Graph ────────────────────────────────────
graph = StateGraph(ReportState)

graph.add_node("ops_agent", ops_node)
graph.add_node("sales_agent", sales_node)
graph.add_node("report_agent", report_node)

graph.set_entry_point("ops_agent")
graph.add_edge("ops_agent", "sales_agent")
graph.add_edge("sales_agent", "report_agent")
graph.add_edge("report_agent", END)

app = graph.compile()

# ── Run ────────────────────────────────────────────
print("\n" + "="*60)
print("AGRAWAL METAL WORKS — AUTONOMOUS WEEKLY REPORT")
print("="*60 + "\n")

result = app.invoke({
    "data": agrawal_data,
    "ops_analysis": "",
    "sales_analysis": "",
    "final_report": ""
})

print("\n")
print(result["final_report"])

# Save to file
filename = f"agrawal_report_{today.replace(' ', '_')}.txt"
with open(filename, "w") as f:
    f.write(result["final_report"])

print(f"\n✅ Report saved to {filename}")