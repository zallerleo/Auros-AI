#!/usr/bin/env python3
"""
AUROS — Savings Dashboard Generator

Combines output from all three analysis tools (Install Analyzer, Consumables
Calculator, Load Planner) into a single executive-level HTML report.

This is the one-page deliverable that demonstrates the gap between current
spend and optimal operations.

Usage:
    python tools/savings_dashboard.py --demo --company "Imagine Exhibits" --show "Cabinet of Curiosities"
    python tools/savings_dashboard.py --install-data install.csv --consumables-data orders.csv --inventory items.csv --company "Client Name"
"""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Ensure project root & tools are importable ────────────────────────────
TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

# ── Import the three analysis tools ──────────────────────────────────────
from install_analyzer import (
    generate_demo_data as ia_demo_data,
    analyze as ia_analyze,
    load_data as ia_load_data,
    InstallReport,
    BENCHMARKS,
)
from consumables_calculator import (
    run_demo as cc_run_demo,
    calculate_quantities as cc_calculate,
    load_history as cc_load_history,
    analyze_history as cc_analyze_history,
    build_recommendation as cc_build_recommendation,
    CONSUMABLES,
)
from load_planner import (
    generate_demo_inventory as lp_demo_inventory,
    analyze as lp_analyze,
    load_inventory_csv as lp_load_csv,
    TRUCK_SPECS,
)


# ═══════════════════════════════════════════════════════════════════════════
#  DATA COLLECTION
# ═══════════════════════════════════════════════════════════════════════════

def collect_demo_data() -> Dict[str, Any]:
    """Run all three tools in demo mode and return combined data."""

    # 1 — Install Analyzer
    meta, items = ia_demo_data()
    install_report: InstallReport = ia_analyze(meta, items)
    install_data = install_report.to_dict()

    # 2 — Consumables Calculator
    consumables_data = cc_run_demo()

    # 3 — Load Planner
    lp_items, current_trucks, cost_per_truck = lp_demo_inventory()
    truck_spec = TRUCK_SPECS["53ft"]
    load_data = lp_analyze(lp_items, truck_spec, current_trucks, cost_per_truck)

    return {
        "install": install_data,
        "consumables": consumables_data,
        "load": load_data,
        "data_source": "demo",
    }


def collect_real_data(
    install_path: Optional[str] = None,
    consumables_path: Optional[str] = None,
    inventory_path: Optional[str] = None,
    sqft: int = 40000,
    zones: int = 15,
    exhibits: int = 200,
    truck_type: str = "53ft",
    current_trucks: int = 40,
    cost_per_truck: float = 2500.0,
    moves_per_year: int = 2,
) -> Dict[str, Any]:
    """Run tools against real data files."""

    # 1 — Install Analyzer
    if install_path:
        meta, items = ia_load_data(install_path)
        meta["moves_per_year"] = moves_per_year
        install_report = ia_analyze(meta, items)
        install_data = install_report.to_dict()
    else:
        meta, items = ia_demo_data()
        install_report = ia_analyze(meta, items)
        install_data = install_report.to_dict()

    # 2 — Consumables Calculator
    calculated = cc_calculate(sqft, zones, exhibits)
    history_analysis = None
    if consumables_path:
        history = cc_load_history(consumables_path)
        history_analysis = cc_analyze_history(history)
    recommendation = cc_build_recommendation(calculated, history_analysis)
    consumables_data = {
        "venue_parameters": {"sqft": sqft, "zones": zones, "exhibits": exhibits},
        "calculated_quantities": calculated,
        "historical_analysis": history_analysis or {},
        "recommendation": recommendation,
    }

    # 3 — Load Planner
    if inventory_path:
        lp_items = lp_load_csv(inventory_path)
    else:
        lp_items, current_trucks, cost_per_truck = lp_demo_inventory()
    truck_spec = TRUCK_SPECS.get(truck_type, TRUCK_SPECS["53ft"])
    load_data = lp_analyze(lp_items, truck_spec, current_trucks, cost_per_truck)

    return {
        "install": install_data,
        "consumables": consumables_data,
        "load": load_data,
        "data_source": "real" if any([install_path, consumables_path, inventory_path]) else "demo",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  SYNTHESIS — derive combined metrics
# ═══════════════════════════════════════════════════════════════════════════

def synthesize(data: Dict[str, Any], company: str, show: str, moves_per_year: int = 2) -> Dict[str, Any]:
    """Combine outputs from all three tools into dashboard-ready structure."""

    inst = data["install"]
    cons = data["consumables"]
    load = data["load"]

    # ── Install totals ────────────────────────────────────────────────
    total_install_cost = inst["summary"]["total_install_cost"]
    total_optimal = inst["summary"]["optimal_cost"]
    total_waste = inst["summary"]["total_identified_waste"]
    waste_pct = inst["summary"]["waste_percentage"]
    annual_savings_install = inst["summary"]["projected_annual_savings"]

    # ── Consumables savings ───────────────────────────────────────────
    rec = cons.get("recommendation", {})
    cons_savings_per_show = rec.get("projected_savings_per_show", 0)
    cons_optimal = rec.get("total_bulk_cost", 0)
    cons_typical = rec.get("estimated_typical_spend", 0)
    cons_annual_savings = cons_savings_per_show * moves_per_year

    # ── Truck savings ─────────────────────────────────────────────────
    load_fin = load.get("financials", {})
    load_analysis = load.get("analysis", {})
    truck_savings_per_move = load_fin.get("savings_per_move", 0)
    truck_annual_savings = truck_savings_per_move * moves_per_year
    trucks_current = load_analysis.get("current_truck_count", 0)
    trucks_optimal = load_analysis.get("optimal_trucks_packed", 0)
    trucks_eliminated = load_analysis.get("trucks_eliminated", 0)
    current_util = load_analysis.get("current_avg_utilization_pct", 0)
    optimal_util = load_analysis.get("optimal_avg_volume_utilization_pct", 0)
    cost_per_truck = load_fin.get("cost_per_truck", 0)

    # ── Grand totals (avoid double-counting: install already includes
    #    consumables + transport categories, so we highlight the delta
    #    from optimized ordering and loading as incremental) ───────────
    # The install report captures category-level waste. The consumables
    # and truck tools provide deeper, item-level optimization on top.
    # We use the install total as the headline and note the additional
    # precision savings from the other two tools.
    grand_annual_savings = annual_savings_install

    # ── Category breakdown from install report ────────────────────────
    categories = []
    for cat in inst.get("categories", []):
        categories.append({
            "label": cat["label"],
            "actual": cat["total_spend"],
            "optimal": cat["optimal_spend"],
            "waste": cat["waste"],
            "waste_pct": cat["waste_pct"],
            "drivers": cat.get("waste_drivers", []),
        })

    # ── Top 5 savings opportunities ──────────────────────────────────
    top5_raw = inst.get("top_5_waste_areas", [])
    top5 = []
    for i, item in enumerate(top5_raw):
        cat_key = item.get("category", "")
        fix_map = {
            "rush_orders": "Pre-order consumables 3-4 weeks ahead of each move. Maintain rolling inventory of high-turnover items.",
            "transportation": "Use load planning software to maximize cubic utilization. Consolidate partial loads.",
            "consumables": "Standardize kitting with per-department allocations. Negotiate bulk purchasing agreements.",
            "labor": "Stagger call times by department. Cross-train crew. Plan advance schedules to cut overtime.",
            "equipment_rentals": "Negotiate annual rental agreements. Purchase frequently-rented items outright.",
            "vendor_contractor": "Rebid contracts annually. Bundle services across departments for volume discounts.",
            "venue_specific": "Negotiate venue packages upfront. Share infrastructure across departments.",
        }
        top5.append({
            "rank": i + 1,
            "description": item["description"],
            "category": cat_key,
            "waste": item["waste_amount"],
            "notes": item.get("notes", ""),
            "fix": fix_map.get(cat_key, "Optimize procurement and scheduling to reduce cost."),
        })

    # ── Consumables detail ────────────────────────────────────────────
    hist = cons.get("historical_analysis", {})
    over_ordered = []
    under_ordered = []
    for iid, stats in hist.get("items", {}).items():
        label = CONSUMABLES.get(iid, {}).get("label", iid)
        avg_ordered = stats.get("avg_ordered", 0)
        avg_used = stats.get("avg_used", 0)
        if avg_ordered > 0 and avg_used > 0:
            ratio = (avg_ordered - avg_used) / avg_used * 100
            if ratio > 10:
                over_ordered.append({"label": label, "pct": round(ratio, 1), "avg_ordered": avg_ordered, "avg_used": avg_used})
            elif ratio < -5:
                under_ordered.append({"label": label, "pct": round(abs(ratio), 1), "avg_ordered": avg_ordered, "avg_used": avg_used})

    over_ordered.sort(key=lambda x: x["pct"], reverse=True)
    under_ordered.sort(key=lambda x: x["pct"], reverse=True)

    rush_cost_total = hist.get("total_rush_cost", 0)

    # ── Recommendations (from install report + custom) ────────────────
    recs_raw = inst.get("recommendations", [])
    recommendations = []

    # Prioritized and enriched recommendations
    priority_recs = [
        {
            "title": "Implement Load Planning Software",
            "detail": f"Current truck utilization is {current_util:.0f}%. Optimized packing achieves {optimal_util:.0f}%, "
                      f"eliminating {trucks_eliminated} trucks per move.",
            "savings": f"${truck_savings_per_move * moves_per_year:,.0f}/year",
            "timeline": "2-4 weeks",
            "roi": "Immediate — first move",
        },
        {
            "title": "Standardize Consumable Ordering",
            "detail": f"Replace gut-feel ordering with data-driven kitting. Eliminates an estimated "
                      f"${cons_savings_per_show:,.0f} in waste per show from over-ordering and rush markups.",
            "savings": f"${cons_annual_savings:,.0f}/year",
            "timeline": "1-2 weeks",
            "roi": "Immediate — next order cycle",
        },
    ]

    for r in recs_raw[:3]:
        # Parse the category from the recommendation text
        parts = r.split(":", 1)
        title = parts[0].strip() if len(parts) > 1 else "Operational Improvement"
        detail = parts[1].strip() if len(parts) > 1 else r
        # Extract savings amount
        import re as _re
        savings_match = _re.search(r'\$[\d,]+', r)
        savings_str = savings_match.group(0) if savings_match else "TBD"
        priority_recs.append({
            "title": f"Optimize {title.title()} Spend",
            "detail": detail,
            "savings": f"{savings_str}/move",
            "timeline": "4-8 weeks",
            "roi": "1-2 move cycles",
        })

    recommendations = priority_recs[:5]

    return {
        "company": company,
        "show": show,
        "date": datetime.now().strftime("%B %d, %Y"),
        "data_source": data["data_source"],
        "moves_per_year": moves_per_year,

        # Hero numbers
        "total_install_cost": total_install_cost,
        "total_optimal": total_optimal,
        "total_waste": total_waste,
        "waste_pct": waste_pct,
        "annual_savings": grand_annual_savings,

        # Category breakdown
        "categories": categories,

        # Top 5
        "top5": top5,

        # Truck
        "trucks_current": trucks_current,
        "trucks_optimal": trucks_optimal,
        "trucks_eliminated": trucks_eliminated,
        "current_util": current_util,
        "optimal_util": optimal_util,
        "cost_per_truck": cost_per_truck,
        "truck_savings_per_move": truck_savings_per_move,
        "truck_annual_savings": truck_annual_savings,

        # Consumables
        "cons_optimal": cons_optimal,
        "cons_typical": cons_typical,
        "cons_savings_per_show": cons_savings_per_show,
        "cons_annual_savings": cons_annual_savings,
        "over_ordered": over_ordered[:8],
        "under_ordered": under_ordered[:5],
        "rush_cost_total": rush_cost_total,

        # Recommendations
        "recommendations": recommendations,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  HTML GENERATION
# ═══════════════════════════════════════════════════════════════════════════

def _f(n: float) -> str:
    """Format number as currency."""
    if abs(n) >= 1_000_000:
        return f"${n:,.0f}"
    return f"${n:,.0f}"


def _pct(n: float) -> str:
    return f"{n:.1f}%"


def generate_html(d: Dict[str, Any]) -> str:
    """Generate the full executive dashboard HTML."""

    # ── Pre-compute values for the template ──────────────────────────
    max_cat_actual = max((c["actual"] for c in d["categories"]), default=1)

    # Category bar rows
    cat_rows = ""
    for c in sorted(d["categories"], key=lambda x: x["waste"], reverse=True):
        actual_w = c["actual"] / max_cat_actual * 100
        optimal_w = c["optimal"] / max_cat_actual * 100
        waste_w = (c["actual"] - c["optimal"]) / max_cat_actual * 100
        cat_rows += f"""
        <div class="cat-row">
            <div class="cat-label">{c['label']}</div>
            <div class="cat-bars">
                <div class="bar-track">
                    <div class="bar-actual" style="width:{actual_w:.1f}%">
                        <span class="bar-val">{_f(c['actual'])}</span>
                    </div>
                    <div class="bar-optimal" style="width:{optimal_w:.1f}%">
                        <span class="bar-val">{_f(c['optimal'])}</span>
                    </div>
                </div>
                <div class="cat-waste">-{_f(c['waste'])} <span class="waste-pct">({_pct(c['waste_pct'])})</span></div>
            </div>
        </div>"""

    # Top 5 cards
    top5_cards = ""
    for opp in d["top5"]:
        top5_cards += f"""
        <div class="opp-card">
            <div class="opp-rank">#{opp['rank']}</div>
            <div class="opp-body">
                <div class="opp-title">{opp['description']}</div>
                <div class="opp-category">{BENCHMARKS.get(opp['category'], {}).get('label', opp['category'].replace('_', ' ').title())}</div>
                <div class="opp-problem">{opp['notes'] if opp['notes'] else 'Spend exceeds industry benchmark for optimized operations.'}</div>
                <div class="opp-savings">{_f(opp['waste'])} waste per move</div>
                <div class="opp-fix"><strong>Fix:</strong> {opp['fix']}</div>
                <div class="opp-projected">Projected savings: <strong>{_f(opp['waste'] * d['moves_per_year'])}/year</strong></div>
            </div>
        </div>"""

    # Truck utilization bars
    truck_bars = ""
    for label, val, color in [
        ("Current", d["current_util"], "#e74c3c"),
        ("Optimized", d["optimal_util"], "#c9a84c"),
    ]:
        truck_bars += f"""
        <div class="util-row">
            <div class="util-label">{label}</div>
            <div class="util-track">
                <div class="util-fill" style="width:{min(val, 100):.1f}%;background:{color}"></div>
            </div>
            <div class="util-val">{val:.1f}%</div>
        </div>"""

    # Over-ordered items
    over_rows = ""
    for item in d["over_ordered"]:
        bar_w = min(item["pct"] / 60 * 100, 100)
        over_rows += f"""
        <div class="cons-row">
            <div class="cons-label">{item['label']}</div>
            <div class="cons-bar-track">
                <div class="cons-bar over" style="width:{bar_w:.0f}%"></div>
            </div>
            <div class="cons-val over-val">+{item['pct']:.0f}% over</div>
        </div>"""

    # Under-ordered items (rush risk)
    under_rows = ""
    for item in d["under_ordered"]:
        bar_w = min(item["pct"] / 30 * 100, 100)
        under_rows += f"""
        <div class="cons-row">
            <div class="cons-label">{item['label']}</div>
            <div class="cons-bar-track">
                <div class="cons-bar under" style="width:{bar_w:.0f}%"></div>
            </div>
            <div class="cons-val under-val">-{item['pct']:.0f}% short &rarr; rush risk</div>
        </div>"""

    # Recommendations
    rec_cards = ""
    for i, r in enumerate(d["recommendations"]):
        rec_cards += f"""
        <div class="rec-card">
            <div class="rec-priority">P{i+1}</div>
            <div class="rec-body">
                <div class="rec-title">{r['title']}</div>
                <div class="rec-detail">{r['detail']}</div>
                <div class="rec-meta">
                    <span class="rec-savings">{r['savings']}</span>
                    <span class="rec-timeline">Timeline: {r['timeline']}</span>
                    <span class="rec-roi">ROI: {r['roi']}</span>
                </div>
            </div>
        </div>"""

    # Executive summary sentences
    top_cat = sorted(d["categories"], key=lambda x: x["waste"], reverse=True)
    summary_sentences = (
        f"Analysis of the <strong>{d['show']}</strong> installation reveals "
        f"<strong>{_f(d['total_waste'])}</strong> in identifiable waste across a "
        f"<strong>{_f(d['total_install_cost'])}</strong> install — representing "
        f"<strong>{_pct(d['waste_pct'])}</strong> of total spend. "
        f"The largest cost gaps are in <strong>{top_cat[0]['label']}</strong> "
        f"({_f(top_cat[0]['waste'])} excess) and <strong>{top_cat[1]['label']}</strong> "
        f"({_f(top_cat[1]['waste'])} excess). "
        f"At <strong>{d['moves_per_year']} moves per year</strong>, implementing the "
        f"recommended optimizations would recover an estimated "
        f"<strong>{_f(d['annual_savings'])}/year</strong> — with the majority of savings "
        f"achievable within the first move cycle."
    )

    data_source_note = (
        "demo data for illustrative purposes"
        if d["data_source"] == "demo"
        else f"actual production data from {d['show']}"
    )

    # ── The full HTML ─────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS — Install Cost Intelligence Report | {d['company']}</title>
<style>
/* ═══════════════════════════════════════════════════════════════════
   AUROS EXECUTIVE DASHBOARD — CORE STYLES
   ═══════════════════════════════════════════════════════════════════ */
:root {{
    --bg:        #0a0a12;
    --bg-card:   #111120;
    --bg-card2:  #161628;
    --gold:      #c9a84c;
    --gold-dim:  #a08838;
    --gold-glow: rgba(201,168,76,0.12);
    --cream:     #f0ece4;
    --cream-dim: #b0a99e;
    --red:       #e74c3c;
    --red-dim:   rgba(231,76,60,0.15);
    --green:     #27ae60;
    --green-dim: rgba(39,174,96,0.15);
    --blue:      #3498db;
    --border:    #1e1e38;
    --font:      'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
    --mono:      'SF Mono', 'Fira Code', 'Consolas', monospace;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    background: var(--bg);
    color: var(--cream);
    font-family: var(--font);
    font-size: 15px;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
}}

.dashboard {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 40px 32px 60px;
}}

/* ── HEADER ─────────────────────────────────────────────────────── */
.header {{
    text-align: center;
    padding-bottom: 48px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 48px;
}}

.logo-line {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    margin-bottom: 8px;
}}

.logo-mark {{
    width: 44px;
    height: 44px;
    border: 2px solid var(--gold);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 18px;
    color: var(--gold);
    letter-spacing: 1px;
}}

.logo-text {{
    font-size: 28px;
    font-weight: 300;
    letter-spacing: 6px;
    text-transform: uppercase;
    color: var(--cream);
}}

.report-title {{
    font-size: 15px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--gold);
    margin-top: 4px;
    font-weight: 500;
}}

.meta-row {{
    display: flex;
    justify-content: center;
    gap: 32px;
    margin-top: 20px;
    font-size: 13px;
    color: var(--cream-dim);
}}

.meta-row span {{ font-weight: 500; color: var(--cream); }}

/* ── HERO NUMBER ────────────────────────────────────────────────── */
.hero {{
    text-align: center;
    margin: 48px 0 56px;
}}

.hero-label {{
    font-size: 13px;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 12px;
    font-weight: 600;
}}

.hero-number {{
    font-size: 72px;
    font-weight: 200;
    color: var(--cream);
    letter-spacing: 2px;
    line-height: 1;
    text-shadow: 0 0 80px var(--gold-glow);
}}

.hero-sub {{
    font-size: 14px;
    color: var(--cream-dim);
    margin-top: 12px;
}}

.hero-sub strong {{
    color: var(--gold);
    font-weight: 600;
}}

/* ── SECTIONS ───────────────────────────────────────────────────── */
.section {{
    margin-bottom: 56px;
}}

.section-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
}}

.section-num {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--gold);
    color: var(--bg);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    font-weight: 700;
    flex-shrink: 0;
}}

.section-title {{
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--cream);
}}

/* ── EXEC SUMMARY ───────────────────────────────────────────────── */
.kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 28px;
}}

.kpi-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}}

.kpi-label {{
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--cream-dim);
    margin-bottom: 8px;
}}

.kpi-value {{
    font-size: 28px;
    font-weight: 300;
    color: var(--cream);
}}

.kpi-value.waste {{ color: var(--red); }}
.kpi-value.savings {{ color: var(--gold); }}

.summary-text {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--gold);
    border-radius: 0 12px 12px 0;
    padding: 24px 28px;
    font-size: 15px;
    line-height: 1.8;
    color: var(--cream-dim);
}}

.summary-text strong {{
    color: var(--cream);
    font-weight: 600;
}}

/* ── COST BREAKDOWN CHART ───────────────────────────────────────── */
.cat-row {{
    display: grid;
    grid-template-columns: 180px 1fr;
    align-items: center;
    margin-bottom: 14px;
}}

.cat-label {{
    font-size: 13px;
    font-weight: 500;
    color: var(--cream);
    text-align: right;
    padding-right: 20px;
}}

.cat-bars {{
    display: flex;
    align-items: center;
    gap: 16px;
}}

.bar-track {{
    flex: 1;
    position: relative;
    height: 36px;
    background: var(--bg-card);
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--border);
}}

.bar-actual {{
    position: absolute;
    top: 0;
    left: 0;
    height: 50%;
    background: linear-gradient(90deg, #e74c3c22, #e74c3c66);
    border-bottom: 1px solid rgba(231,76,60,0.3);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 8px;
}}

.bar-optimal {{
    position: absolute;
    top: 50%;
    left: 0;
    height: 50%;
    background: linear-gradient(90deg, rgba(201,168,76,0.1), rgba(201,168,76,0.4));
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 8px;
}}

.bar-val {{
    font-size: 10px;
    font-family: var(--mono);
    color: var(--cream);
    white-space: nowrap;
    opacity: 0.9;
}}

.cat-waste {{
    min-width: 140px;
    font-size: 13px;
    font-family: var(--mono);
    color: var(--red);
    font-weight: 600;
    white-space: nowrap;
}}

.waste-pct {{
    color: var(--cream-dim);
    font-weight: 400;
    font-size: 11px;
}}

.chart-legend {{
    display: flex;
    gap: 24px;
    margin-top: 16px;
    padding-left: 200px;
    font-size: 12px;
    color: var(--cream-dim);
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
}}

.legend-swatch {{
    width: 14px;
    height: 8px;
    border-radius: 2px;
}}

.legend-swatch.actual {{ background: linear-gradient(90deg, #e74c3c44, #e74c3c88); }}
.legend-swatch.optimal {{ background: linear-gradient(90deg, rgba(201,168,76,0.2), rgba(201,168,76,0.6)); }}

/* ── TOP 5 CARDS ────────────────────────────────────────────────── */
.opp-card {{
    display: grid;
    grid-template-columns: 56px 1fr;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 12px;
    overflow: hidden;
}}

.opp-rank {{
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-card2);
    font-size: 18px;
    font-weight: 700;
    color: var(--gold);
    border-right: 1px solid var(--border);
}}

.opp-body {{
    padding: 18px 24px;
}}

.opp-title {{
    font-size: 15px;
    font-weight: 600;
    color: var(--cream);
    margin-bottom: 4px;
}}

.opp-category {{
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--gold-dim);
    margin-bottom: 8px;
}}

.opp-problem {{
    font-size: 13px;
    color: var(--cream-dim);
    margin-bottom: 8px;
    line-height: 1.5;
}}

.opp-savings {{
    display: inline-block;
    background: var(--red-dim);
    color: var(--red);
    font-weight: 700;
    font-size: 14px;
    padding: 4px 12px;
    border-radius: 6px;
    margin-bottom: 8px;
}}

.opp-fix {{
    font-size: 13px;
    color: var(--cream-dim);
    margin-bottom: 6px;
    line-height: 1.5;
}}

.opp-projected {{
    font-size: 13px;
    color: var(--green);
}}

/* ── TRUCK SECTION ──────────────────────────────────────────────── */
.truck-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 28px;
}}

.truck-stat {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    text-align: center;
}}

.truck-stat-label {{
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--cream-dim);
    margin-bottom: 8px;
}}

.truck-stat-value {{
    font-size: 36px;
    font-weight: 300;
    color: var(--cream);
}}

.truck-stat-value.highlight {{ color: var(--gold); }}
.truck-stat-value.negative {{ color: var(--red); }}

.truck-stat-sub {{
    font-size: 12px;
    color: var(--cream-dim);
    margin-top: 4px;
}}

.util-row {{
    display: grid;
    grid-template-columns: 100px 1fr 60px;
    align-items: center;
    margin-bottom: 10px;
}}

.util-label {{
    font-size: 13px;
    color: var(--cream);
    font-weight: 500;
}}

.util-track {{
    height: 24px;
    background: var(--bg-card);
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid var(--border);
}}

.util-fill {{
    height: 100%;
    border-radius: 6px 0 0 6px;
    transition: width 0.5s ease;
}}

.util-val {{
    text-align: right;
    font-family: var(--mono);
    font-size: 13px;
    color: var(--cream);
    font-weight: 600;
}}

/* ── CONSUMABLES SECTION ────────────────────────────────────────── */
.cons-split {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}}

.cons-column {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
}}

.cons-col-title {{
    font-size: 13px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 16px;
    font-weight: 600;
}}

.cons-row {{
    display: grid;
    grid-template-columns: 140px 1fr 120px;
    align-items: center;
    margin-bottom: 8px;
}}

.cons-label {{
    font-size: 12px;
    color: var(--cream);
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}}

.cons-bar-track {{
    height: 12px;
    background: var(--bg-card2);
    border-radius: 4px;
    overflow: hidden;
}}

.cons-bar {{
    height: 100%;
    border-radius: 4px;
}}

.cons-bar.over {{ background: linear-gradient(90deg, #e74c3c66, #e74c3c); }}
.cons-bar.under {{ background: linear-gradient(90deg, #f39c1266, #f39c12); }}

.cons-val {{
    font-size: 11px;
    font-family: var(--mono);
    text-align: right;
    font-weight: 600;
    white-space: nowrap;
}}

.over-val {{ color: var(--red); }}
.under-val {{ color: #f39c12; }}

.cons-summary-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
}}

.cons-summary-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
}}

.cons-summary-label {{
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--cream-dim);
    margin-bottom: 6px;
}}

.cons-summary-value {{
    font-size: 24px;
    font-weight: 300;
    color: var(--cream);
}}

.cons-summary-value.gold {{ color: var(--gold); }}

/* ── RECOMMENDATIONS ────────────────────────────────────────────── */
.rec-card {{
    display: grid;
    grid-template-columns: 48px 1fr;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 12px;
    overflow: hidden;
}}

.rec-priority {{
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--gold);
    color: var(--bg);
    font-weight: 800;
    font-size: 14px;
    border-right: 1px solid var(--border);
}}

.rec-body {{
    padding: 18px 24px;
}}

.rec-title {{
    font-size: 15px;
    font-weight: 700;
    color: var(--cream);
    margin-bottom: 6px;
}}

.rec-detail {{
    font-size: 13px;
    color: var(--cream-dim);
    line-height: 1.6;
    margin-bottom: 12px;
}}

.rec-meta {{
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}}

.rec-meta span {{
    font-size: 12px;
    padding: 4px 12px;
    border-radius: 6px;
    font-weight: 600;
}}

.rec-savings {{
    background: var(--green-dim);
    color: var(--green);
}}

.rec-timeline {{
    background: rgba(52,152,219,0.12);
    color: var(--blue);
}}

.rec-roi {{
    background: var(--gold-glow);
    color: var(--gold);
}}

/* ── FOOTER ─────────────────────────────────────────────────────── */
.footer {{
    margin-top: 64px;
    padding-top: 32px;
    border-top: 1px solid var(--border);
    text-align: center;
}}

.footer-brand {{
    font-size: 14px;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: var(--gold);
    font-weight: 500;
    margin-bottom: 12px;
}}

.footer-note {{
    font-size: 12px;
    color: var(--cream-dim);
    line-height: 1.8;
}}

.footer-note a {{
    color: var(--gold);
    text-decoration: none;
}}

.footer-note a:hover {{
    text-decoration: underline;
}}

/* ── DIVIDER ────────────────────────────────────────────────────── */
.divider {{
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 40px 0;
}}

/* ═══════════════════════════════════════════════════════════════════
   PRINT STYLES
   ═══════════════════════════════════════════════════════════════════ */
@media print {{
    :root {{
        --bg:       #ffffff;
        --bg-card:  #f8f8f8;
        --bg-card2: #f0f0f0;
        --cream:    #1a1a1a;
        --cream-dim:#555555;
        --border:   #e0e0e0;
        --gold:     #b8941f;
        --gold-dim: #96780f;
        --gold-glow: rgba(184,148,31,0.08);
        --red:      #c0392b;
        --red-dim:  rgba(192,57,43,0.08);
        --green:    #1e8449;
        --green-dim: rgba(30,132,73,0.08);
        --blue:     #2471a3;
    }}

    body {{
        font-size: 11px;
        background: white;
        color: #1a1a1a;
    }}

    .dashboard {{
        max-width: 100%;
        padding: 20px;
    }}

    .hero-number {{
        font-size: 48px;
        text-shadow: none;
    }}

    .section {{ margin-bottom: 28px; }}
    .kpi-grid {{ gap: 8px; }}
    .kpi-value {{ font-size: 20px; }}
    .truck-grid {{ gap: 10px; }}
    .truck-stat-value {{ font-size: 24px; }}

    .opp-card, .rec-card {{
        break-inside: avoid;
    }}

    .section {{
        break-inside: avoid;
    }}

    @page {{
        margin: 1cm;
        size: A4;
    }}
}}

/* ═══════════════════════════════════════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {{
    .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .truck-grid {{ grid-template-columns: 1fr; }}
    .cons-split {{ grid-template-columns: 1fr; }}
    .cat-row {{ grid-template-columns: 1fr; }}
    .cat-label {{ text-align: left; padding-right: 0; margin-bottom: 4px; }}
    .meta-row {{ flex-direction: column; gap: 4px; }}
    .hero-number {{ font-size: 48px; }}
    .chart-legend {{ padding-left: 0; }}
    .cons-row {{ grid-template-columns: 110px 1fr 100px; }}
}}
</style>
</head>
<body>
<div class="dashboard">

    <!-- ═══ HEADER ═══ -->
    <div class="header">
        <div class="logo-line">
            <div class="logo-mark">A</div>
            <div class="logo-text">AUROS</div>
        </div>
        <div class="report-title">Install Cost Intelligence Report</div>
        <div class="meta-row">
            <div>Prepared for <span>{d['company']}</span></div>
            <div>Show: <span>{d['show']}</span></div>
            <div><span>{d['date']}</span></div>
        </div>
    </div>

    <!-- ═══ HERO ═══ -->
    <div class="hero">
        <div class="hero-label">Total Identified Savings</div>
        <div class="hero-number">{_f(d['annual_savings'])}</div>
        <div class="hero-sub">per year &mdash; based on <strong>{d['moves_per_year']} moves/year</strong> at {_pct(d['waste_pct'])} waste identified per install</div>
    </div>

    <!-- ═══ SECTION 1: EXECUTIVE SUMMARY ═══ -->
    <div class="section">
        <div class="section-header">
            <div class="section-num">1</div>
            <div class="section-title">Executive Summary</div>
        </div>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">Total Install Cost</div>
                <div class="kpi-value">{_f(d['total_install_cost'])}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Waste Identified</div>
                <div class="kpi-value waste">{_f(d['total_waste'])}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Waste Percentage</div>
                <div class="kpi-value waste">{_pct(d['waste_pct'])}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">Annual Savings</div>
                <div class="kpi-value savings">{_f(d['annual_savings'])}</div>
            </div>
        </div>
        <div class="summary-text">{summary_sentences}</div>
    </div>

    <!-- ═══ SECTION 2: COST BREAKDOWN ═══ -->
    <div class="section">
        <div class="section-header">
            <div class="section-num">2</div>
            <div class="section-title">Cost Breakdown by Category</div>
        </div>
        {cat_rows}
        <div class="chart-legend">
            <div class="legend-item"><div class="legend-swatch actual"></div> Actual Spend</div>
            <div class="legend-item"><div class="legend-swatch optimal"></div> Optimal Spend</div>
        </div>
    </div>

    <!-- ═══ SECTION 3: TOP 5 SAVINGS ═══ -->
    <div class="section">
        <div class="section-header">
            <div class="section-num">3</div>
            <div class="section-title">Top 5 Savings Opportunities</div>
        </div>
        {top5_cards}
    </div>

    <!-- ═══ SECTION 4: TRUCK OPTIMIZATION ═══ -->
    <div class="section">
        <div class="section-header">
            <div class="section-num">4</div>
            <div class="section-title">Truck Optimization</div>
        </div>
        <div class="truck-grid">
            <div class="truck-stat">
                <div class="truck-stat-label">Current Trucks</div>
                <div class="truck-stat-value negative">{d['trucks_current']}</div>
                <div class="truck-stat-sub">at {_pct(d['current_util'])} avg utilization</div>
            </div>
            <div class="truck-stat">
                <div class="truck-stat-label">Optimal Trucks</div>
                <div class="truck-stat-value highlight">{d['trucks_optimal']}</div>
                <div class="truck-stat-sub">at {_pct(d['optimal_util'])} avg utilization</div>
            </div>
            <div class="truck-stat">
                <div class="truck-stat-label">Trucks Eliminated</div>
                <div class="truck-stat-value highlight">{d['trucks_eliminated']}</div>
                <div class="truck-stat-sub">at {_f(d['cost_per_truck'])} each</div>
            </div>
            <div class="truck-stat">
                <div class="truck-stat-label">Annual Savings</div>
                <div class="truck-stat-value highlight">{_f(d['truck_annual_savings'])}</div>
                <div class="truck-stat-sub">{d['moves_per_year']} moves/year</div>
            </div>
        </div>
        <div style="background:var(--bg-card);border:1px solid var(--border);border-radius:12px;padding:24px;margin-top:8px;">
            <div style="font-size:13px;letter-spacing:2px;text-transform:uppercase;color:var(--gold);margin-bottom:16px;font-weight:600;">Volume Utilization</div>
            {truck_bars}
        </div>
    </div>

    <!-- ═══ SECTION 5: CONSUMABLES ═══ -->
    <div class="section">
        <div class="section-header">
            <div class="section-num">5</div>
            <div class="section-title">Consumables Optimization</div>
        </div>
        <div class="cons-split">
            <div class="cons-column">
                <div class="cons-col-title">Over-Ordered Items</div>
                {over_rows if over_rows else '<div style="color:var(--cream-dim);font-size:13px;">No significant over-ordering detected.</div>'}
            </div>
            <div class="cons-column">
                <div class="cons-col-title">Under-Ordered (Rush Risk)</div>
                {under_rows if under_rows else '<div style="color:var(--cream-dim);font-size:13px;">No significant under-ordering detected.</div>'}
            </div>
        </div>
        <div class="cons-summary-grid">
            <div class="cons-summary-card">
                <div class="cons-summary-label">Optimized Order Cost</div>
                <div class="cons-summary-value gold">{_f(d['cons_optimal'])}</div>
            </div>
            <div class="cons-summary-card">
                <div class="cons-summary-label">Typical (Unoptimized)</div>
                <div class="cons-summary-value">{_f(d['cons_typical'])}</div>
            </div>
            <div class="cons-summary-card">
                <div class="cons-summary-label">Rush Order Costs (6 shows)</div>
                <div class="cons-summary-value" style="color:var(--red);">{_f(d['rush_cost_total'])}</div>
            </div>
        </div>
    </div>

    <!-- ═══ SECTION 6: RECOMMENDATIONS ═══ -->
    <div class="section">
        <div class="section-header">
            <div class="section-num">6</div>
            <div class="section-title">Prioritized Recommendations</div>
        </div>
        {rec_cards}
    </div>

    <!-- ═══ FOOTER ═══ -->
    <div class="footer">
        <div class="footer-brand">Prepared by AUROS</div>
        <div class="footer-note">
            This analysis is based on {data_source_note}.<br>
            Savings projections represent achievable targets based on industry benchmarks for optimized operations.<br>
            <a href="mailto:hello@auros.ai">hello@auros.ai</a>
        </div>
    </div>

</div>
</body>
</html>"""

    return html


# ═══════════════════════════════════════════════════════════════════════════
#  FILE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

def save_report(html: str, company: str) -> str:
    """Save HTML to portfolio directory and return the path."""
    safe_company = re.sub(r'[^a-zA-Z0-9_-]', '_', company.lower().strip())
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"savings_report_{safe_company}_{date_str}.html"

    out_dir = PROJECT_ROOT / "portfolio"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    return str(out_path)


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="AUROS — Combined Savings Dashboard Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/savings_dashboard.py --demo --company "Imagine Exhibits" --show "Cabinet of Curiosities"
  python tools/savings_dashboard.py --install-data install.csv --consumables-data orders.csv --inventory items.csv --company "Client Name"
        """,
    )

    # Mode
    parser.add_argument("--demo", action="store_true", help="Run all tools in demo mode")

    # Data paths
    parser.add_argument("--install-data", type=str, help="Path to install cost CSV/Excel")
    parser.add_argument("--consumables-data", type=str, help="Path to consumables history CSV")
    parser.add_argument("--inventory", type=str, help="Path to truck inventory CSV")

    # Metadata
    parser.add_argument("--company", type=str, default="Demo Client", help="Company name")
    parser.add_argument("--show", type=str, default="Demo Show", help="Show / event name")
    parser.add_argument("--moves", type=int, default=2, help="Moves per year (default 2)")

    # Venue params (for consumables)
    parser.add_argument("--sqft", type=int, default=40000, help="Venue square footage")
    parser.add_argument("--zones", type=int, default=15, help="Number of zones")
    parser.add_argument("--exhibits", type=int, default=200, help="Number of exhibits")

    # Truck params
    parser.add_argument("--truck-type", type=str, default="53ft", choices=list(TRUCK_SPECS.keys()))
    parser.add_argument("--current-trucks", type=int, default=40, help="Current truck count")
    parser.add_argument("--cost-per-truck", type=float, default=2500.0, help="Cost per truck")

    # Output
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: portfolio/)")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  AUROS — Savings Dashboard Generator")
    print("=" * 60)

    # Collect data
    if args.demo:
        print("\n  Running all three tools in demo mode...")
        data = collect_demo_data()
    else:
        print("\n  Running analysis with provided data...")
        data = collect_real_data(
            install_path=args.install_data,
            consumables_path=args.consumables_data,
            inventory_path=args.inventory,
            sqft=args.sqft,
            zones=args.zones,
            exhibits=args.exhibits,
            truck_type=args.truck_type,
            current_trucks=args.current_trucks,
            cost_per_truck=args.cost_per_truck,
            moves_per_year=args.moves,
        )

    print("  [OK] Install Analyzer complete")
    print("  [OK] Consumables Calculator complete")
    print("  [OK] Load Planner complete")

    # Synthesize
    print("\n  Synthesizing combined report...")
    dashboard = synthesize(data, args.company, args.show, args.moves)

    # Generate HTML
    print("  Generating executive dashboard...")
    html = generate_html(dashboard)

    # Save
    if args.output:
        out_path = args.output
        out_dir = os.path.dirname(out_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
    else:
        out_path = save_report(html, args.company)

    print(f"\n  Dashboard saved to: {out_path}")
    print(f"\n  Key metrics:")
    print(f"    Total Install Cost:     {_f(dashboard['total_install_cost'])}")
    print(f"    Waste Identified:       {_f(dashboard['total_waste'])} ({_pct(dashboard['waste_pct'])})")
    print(f"    Annual Savings:         {_f(dashboard['annual_savings'])}")
    print(f"    Trucks Eliminated:      {dashboard['trucks_eliminated']} per move")
    print(f"    Consumables Savings:    {_f(dashboard['cons_savings_per_show'])}/show")
    print("\n" + "=" * 60 + "\n")

    return out_path


if __name__ == "__main__":
    main()
