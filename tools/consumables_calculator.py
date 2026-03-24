#!/usr/bin/env python3
"""
AUROS AI — Consumables Calculator for Live Entertainment Production

Calculates material order quantities for venue installations based on
venue parameters, compares against historical orders, and generates
optimized order recommendations with projected savings.

Usage:
    python consumables_calculator.py --demo
    python consumables_calculator.py --sqft 40000 --zones 15 --exhibits 200 --type convention_center
    python consumables_calculator.py --sqft 40000 --zones 15 --exhibits 200 --history past_orders.csv
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# CONSUMABLE DEFINITIONS
# ---------------------------------------------------------------------------
# Each consumable has:
#   unit        — what we order in
#   base_rate   — baseline quantity per 1,000 sq ft (or per exhibit, per zone, etc.)
#   driver      — primary sizing driver: "sqft", "zones", "exhibits", "fixed", "distance"
#   sub_items   — variants within the category
#   bulk_price  — typical bulk price per unit
#   rush_markup — multiplier when rush-ordered (2-3x is industry norm)
#   buffer_rec  — recommended safety-stock buffer %

CONSUMABLES = {
    "tape_gaffer": {
        "label": "Gaffer Tape",
        "unit": "rolls",
        "driver": "sqft",
        "base_rate": 0.8,          # rolls per 1,000 sq ft
        "bulk_price": 14.50,
        "rush_markup": 2.2,
        "buffer_rec": 0.10,
    },
    "tape_spike": {
        "label": "Spike Tape",
        "unit": "rolls",
        "driver": "zones",
        "base_rate": 3.0,          # rolls per zone
        "bulk_price": 6.75,
        "rush_markup": 2.0,
        "buffer_rec": 0.10,
    },
    "tape_double_sided": {
        "label": "Double-Sided Tape",
        "unit": "rolls",
        "driver": "exhibits",
        "base_rate": 0.15,         # rolls per exhibit piece
        "bulk_price": 8.25,
        "rush_markup": 2.5,
        "buffer_rec": 0.10,
    },
    "tape_masking": {
        "label": "Masking Tape",
        "unit": "rolls",
        "driver": "sqft",
        "base_rate": 0.35,         # rolls per 1,000 sq ft
        "bulk_price": 5.50,
        "rush_markup": 2.0,
        "buffer_rec": 0.10,
    },
    "screws_drywall": {
        "label": "Drywall Screws",
        "unit": "boxes (100ct)",
        "driver": "zones",
        "base_rate": 2.5,          # boxes per zone
        "bulk_price": 9.80,
        "rush_markup": 2.0,
        "buffer_rec": 0.10,
    },
    "screws_wood": {
        "label": "Wood Screws (assorted)",
        "unit": "boxes (100ct)",
        "driver": "zones",
        "base_rate": 1.8,
        "bulk_price": 11.50,
        "rush_markup": 2.0,
        "buffer_rec": 0.10,
    },
    "screws_machine": {
        "label": "Machine Screws / Bolts",
        "unit": "boxes (50ct)",
        "driver": "exhibits",
        "base_rate": 0.06,         # boxes per exhibit
        "bulk_price": 13.25,
        "rush_markup": 2.5,
        "buffer_rec": 0.15,
    },
    "foam_protective": {
        "label": "Protective Foam Wrap",
        "unit": "sheets (4x8 ft)",
        "driver": "exhibits",
        "base_rate": 0.6,          # sheets per exhibit piece
        "bulk_price": 7.40,
        "rush_markup": 2.5,
        "buffer_rec": 0.10,
    },
    "foam_padding": {
        "label": "Display Padding / Cushion",
        "unit": "sheets (4x8 ft)",
        "driver": "exhibits",
        "base_rate": 0.3,
        "bulk_price": 9.20,
        "rush_markup": 2.5,
        "buffer_rec": 0.10,
    },
    "carts": {
        "label": "Utility Carts",
        "unit": "units",
        "driver": "distance",      # more carts for longer dock-to-install runs
        "base_rate": 1.0,          # 1 cart per 100 ft of dock distance
        "bulk_price": 185.00,
        "rush_markup": 1.5,        # rental premium
        "buffer_rec": 0.15,
    },
    "crates": {
        "label": "Shipping Crates",
        "unit": "units",
        "driver": "exhibits",
        "base_rate": 0.25,         # 1 crate per ~4 exhibits
        "bulk_price": 65.00,
        "rush_markup": 2.0,
        "buffer_rec": 0.05,
    },
    "cat6_cable": {
        "label": "Cat-6 Cable",
        "unit": "feet",
        "driver": "sqft",
        "base_rate": 25.0,         # feet of cable per 1,000 sq ft of venue
        "bulk_price": 0.18,        # per foot
        "rush_markup": 3.0,
        "buffer_rec": 0.15,
    },
    "paint_touchup": {
        "label": "Paint / Touch-up",
        "unit": "gallons",
        "driver": "sqft",
        "base_rate": 0.12,         # gallons per 1,000 sq ft
        "bulk_price": 38.00,
        "rush_markup": 2.0,
        "buffer_rec": 0.10,
    },
    "zip_ties": {
        "label": "Zip Ties",
        "unit": "packs (100ct)",
        "driver": "sqft",
        "base_rate": 0.5,          # packs per 1,000 sq ft
        "bulk_price": 4.50,
        "rush_markup": 2.0,
        "buffer_rec": 0.10,
    },
    "velcro_strips": {
        "label": "Velcro Strips",
        "unit": "packs (25ct)",
        "driver": "exhibits",
        "base_rate": 0.2,          # packs per exhibit
        "bulk_price": 8.90,
        "rush_markup": 2.5,
        "buffer_rec": 0.10,
    },
    "cable_management": {
        "label": "Cable Management (raceways, clips)",
        "unit": "kits",
        "driver": "zones",
        "base_rate": 2.0,          # kits per zone
        "bulk_price": 22.00,
        "rush_markup": 2.5,
        "buffer_rec": 0.10,
    },
    "batteries_aa": {
        "label": "Batteries — AA",
        "unit": "packs (24ct)",
        "driver": "exhibits",
        "base_rate": 0.08,
        "bulk_price": 14.00,
        "rush_markup": 2.0,
        "buffer_rec": 0.15,
    },
    "batteries_9v": {
        "label": "Batteries — 9V",
        "unit": "packs (8ct)",
        "driver": "zones",
        "base_rate": 0.5,
        "bulk_price": 16.50,
        "rush_markup": 2.0,
        "buffer_rec": 0.15,
    },
    "cleaning_general": {
        "label": "Cleaning Supplies (general)",
        "unit": "kits",
        "driver": "sqft",
        "base_rate": 0.15,
        "bulk_price": 28.00,
        "rush_markup": 1.8,
        "buffer_rec": 0.10,
    },
    "cleaning_glass": {
        "label": "Glass / Screen Cleaner",
        "unit": "bottles",
        "driver": "exhibits",
        "base_rate": 0.05,
        "bulk_price": 6.50,
        "rush_markup": 1.5,
        "buffer_rec": 0.10,
    },
}

# ---------------------------------------------------------------------------
# VENUE TYPE MULTIPLIERS
# ---------------------------------------------------------------------------
# Different venue types have different consumable profiles. These multiply
# the base calculation.

VENUE_MULTIPLIERS = {
    "convention_center": {
        "tape_gaffer": 1.0, "tape_spike": 1.0, "tape_double_sided": 1.0,
        "tape_masking": 1.0, "screws_drywall": 1.2, "screws_wood": 0.8,
        "screws_machine": 1.0, "foam_protective": 1.0, "foam_padding": 1.0,
        "carts": 1.3, "crates": 1.0, "cat6_cable": 1.2,
        "paint_touchup": 0.6, "zip_ties": 1.1, "velcro_strips": 1.0,
        "cable_management": 1.2, "batteries_aa": 1.0, "batteries_9v": 1.0,
        "cleaning_general": 1.0, "cleaning_glass": 1.0,
    },
    "museum": {
        "tape_gaffer": 0.7, "tape_spike": 0.8, "tape_double_sided": 1.3,
        "tape_masking": 1.4, "screws_drywall": 0.6, "screws_wood": 0.5,
        "screws_machine": 0.8, "foam_protective": 1.5, "foam_padding": 1.5,
        "carts": 1.0, "crates": 1.2, "cat6_cable": 0.8,
        "paint_touchup": 1.5, "zip_ties": 0.7, "velcro_strips": 1.3,
        "cable_management": 0.8, "batteries_aa": 1.2, "batteries_9v": 0.8,
        "cleaning_general": 1.3, "cleaning_glass": 1.8,
    },
    "warehouse": {
        "tape_gaffer": 1.4, "tape_spike": 1.3, "tape_double_sided": 0.8,
        "tape_masking": 0.8, "screws_drywall": 0.5, "screws_wood": 1.5,
        "screws_machine": 1.3, "foam_protective": 0.8, "foam_padding": 0.7,
        "carts": 1.5, "crates": 1.0, "cat6_cable": 1.5,
        "paint_touchup": 0.4, "zip_ties": 1.4, "velcro_strips": 0.8,
        "cable_management": 1.4, "batteries_aa": 0.8, "batteries_9v": 0.8,
        "cleaning_general": 0.8, "cleaning_glass": 0.5,
    },
    "theater": {
        "tape_gaffer": 1.3, "tape_spike": 1.5, "tape_double_sided": 1.0,
        "tape_masking": 1.2, "screws_drywall": 0.8, "screws_wood": 1.0,
        "screws_machine": 0.7, "foam_protective": 1.0, "foam_padding": 1.0,
        "carts": 0.8, "crates": 0.9, "cat6_cable": 1.0,
        "paint_touchup": 1.2, "zip_ties": 1.0, "velcro_strips": 1.0,
        "cable_management": 1.0, "batteries_aa": 1.5, "batteries_9v": 1.5,
        "cleaning_general": 1.1, "cleaning_glass": 0.8,
    },
}

# Complexity multiplier applied globally
COMPLEXITY_MULTIPLIERS = {
    "simple": 0.85,
    "moderate": 1.0,
    "complex": 1.25,
}

# Venue condition affects paint, cleaning, tape, foam
CONDITION_AFFECTED = {
    "paint_touchup", "cleaning_general", "cleaning_glass",
    "tape_masking", "foam_padding", "tape_gaffer",
}
CONDITION_MULTIPLIERS = {
    "new": 0.5,
    "good": 1.0,
    "needs_work": 1.6,
}


# ---------------------------------------------------------------------------
# CORE CALCULATION ENGINE
# ---------------------------------------------------------------------------

def calculate_quantities(
    sqft: int,
    zones: int,
    exhibits: int,
    venue_type: str = "convention_center",
    complexity: str = "moderate",
    condition: str = "good",
    dock_distance_ft: int = 200,
) -> Dict[str, dict]:
    """
    Calculate recommended order quantities for every consumable.

    Returns dict keyed by consumable ID with fields:
        raw_qty, buffered_qty, buffer_pct, unit, label, unit_cost, line_total
    """
    venue_mult = VENUE_MULTIPLIERS.get(venue_type, VENUE_MULTIPLIERS["convention_center"])
    complexity_mult = COMPLEXITY_MULTIPLIERS.get(complexity, 1.0)
    condition_mult = CONDITION_MULTIPLIERS.get(condition, 1.0)

    results = {}

    for cid, spec in CONSUMABLES.items():
        # Base quantity from driver
        if spec["driver"] == "sqft":
            raw = spec["base_rate"] * (sqft / 1000.0)
        elif spec["driver"] == "zones":
            raw = spec["base_rate"] * zones
        elif spec["driver"] == "exhibits":
            raw = spec["base_rate"] * exhibits
        elif spec["driver"] == "distance":
            raw = spec["base_rate"] * (dock_distance_ft / 100.0)
        elif spec["driver"] == "fixed":
            raw = spec["base_rate"]
        else:
            raw = spec["base_rate"]

        # Apply venue-type multiplier
        raw *= venue_mult.get(cid, 1.0)

        # Apply complexity multiplier
        raw *= complexity_mult

        # Apply condition multiplier (only for affected categories)
        if cid in CONDITION_AFFECTED:
            raw *= condition_mult

        # Round up — you can't order 0.3 of a roll
        raw_rounded = math.ceil(raw)

        # Apply recommended buffer
        buffer_pct = spec["buffer_rec"]
        buffered = math.ceil(raw_rounded * (1 + buffer_pct))

        results[cid] = {
            "label": spec["label"],
            "unit": spec["unit"],
            "raw_qty": raw_rounded,
            "buffer_pct": buffer_pct,
            "buffered_qty": buffered,
            "unit_cost": spec["bulk_price"],
            "line_total": round(buffered * spec["bulk_price"], 2),
            "rush_markup": spec["rush_markup"],
        }

    return results


# ---------------------------------------------------------------------------
# HISTORICAL COMPARISON
# ---------------------------------------------------------------------------

def load_history(csv_path: str) -> List[Dict]:
    """
    Load historical order CSV.  Expected columns:
        show_name, item_id, ordered_qty, used_qty, rush_qty, rush_unit_cost
    """
    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "show_name": row.get("show_name", ""),
                "item_id": row.get("item_id", ""),
                "ordered_qty": int(row.get("ordered_qty", 0)),
                "used_qty": int(row.get("used_qty", 0)),
                "rush_qty": int(row.get("rush_qty", 0)),
                "rush_unit_cost": float(row.get("rush_unit_cost", 0)),
            })
    return rows


def analyze_history(history: List[Dict]) -> Dict:
    """
    Aggregate historical orders to find over/under patterns per item.
    Returns per-item stats and total rush cost.
    """
    items: Dict[str, dict] = {}
    total_rush_cost = 0.0

    for row in history:
        iid = row["item_id"]
        if iid not in items:
            items[iid] = {
                "label": CONSUMABLES[iid]["label"] if iid in CONSUMABLES else iid,
                "total_ordered": 0,
                "total_used": 0,
                "total_rush_qty": 0,
                "total_rush_cost": 0.0,
                "show_count": 0,
            }
        items[iid]["total_ordered"] += row["ordered_qty"]
        items[iid]["total_used"] += row["used_qty"]
        items[iid]["total_rush_qty"] += row["rush_qty"]
        rush_line = row["rush_qty"] * row["rush_unit_cost"]
        items[iid]["total_rush_cost"] += rush_line
        items[iid]["show_count"] += 1
        total_rush_cost += rush_line

    # Compute percentages
    analysis = {}
    for iid, s in items.items():
        over = s["total_ordered"] - s["total_used"]
        if s["total_used"] > 0:
            over_pct = round((over / s["total_used"]) * 100, 1) if over > 0 else 0.0
            under_pct = round((s["total_rush_qty"] / s["total_used"]) * 100, 1) if s["total_rush_qty"] > 0 else 0.0
        else:
            over_pct = 100.0 if over > 0 else 0.0
            under_pct = 0.0

        analysis[iid] = {
            "label": s["label"],
            "total_ordered": s["total_ordered"],
            "total_used": s["total_used"],
            "surplus": max(over, 0),
            "over_order_pct": over_pct,
            "rush_qty": s["total_rush_qty"],
            "under_order_pct": under_pct,
            "rush_cost": round(s["total_rush_cost"], 2),
            "shows_analyzed": s["show_count"],
        }

    patterns = _detect_patterns(analysis)

    return {
        "per_item": analysis,
        "total_rush_cost": round(total_rush_cost, 2),
        "patterns": patterns,
    }


def _detect_patterns(analysis: Dict) -> List[str]:
    """Generate human-readable pattern insights."""
    patterns = []
    for iid, a in analysis.items():
        if a["over_order_pct"] >= 20:
            patterns.append(
                f"You consistently over-order {a['label']} by ~{a['over_order_pct']}%."
            )
        if a["under_order_pct"] >= 15:
            patterns.append(
                f"You consistently under-order {a['label']} by ~{a['under_order_pct']}%, "
                f"incurring ${a['rush_cost']:,.2f} in rush fees over {a['shows_analyzed']} shows."
            )
    return patterns


# ---------------------------------------------------------------------------
# ORDER RECOMMENDATION
# ---------------------------------------------------------------------------

def build_recommendation(
    calculated: Dict[str, dict],
    history_analysis: Optional[Dict] = None,
) -> Dict:
    """
    Build the final order recommendation with savings projections.
    """
    total_bulk = 0.0
    total_if_typical = 0.0  # what they'd spend with their usual over/under pattern
    lines = []

    for cid, calc in calculated.items():
        bulk_line = calc["line_total"]
        total_bulk += bulk_line

        # Estimate what typical (un-optimized) spend looks like
        # Assume 35% average over-order + some rush cost
        typical_over = calc["buffered_qty"] * 1.35
        typical_base = typical_over * calc["unit_cost"]
        # Plus assume 8% of quantity ends up rush-ordered at markup
        rush_portion = calc["buffered_qty"] * 0.08
        typical_rush = rush_portion * calc["unit_cost"] * calc["rush_markup"]
        typical_line = typical_base + typical_rush
        total_if_typical += typical_line

        lines.append({
            "item_id": cid,
            "label": calc["label"],
            "unit": calc["unit"],
            "recommended_qty": calc["buffered_qty"],
            "buffer_pct": f"{int(calc['buffer_pct'] * 100)}%",
            "unit_cost": calc["unit_cost"],
            "line_total": bulk_line,
        })

    savings_per_show = round(total_if_typical - total_bulk, 2)

    rec = {
        "order_lines": lines,
        "total_bulk_cost": round(total_bulk, 2),
        "estimated_typical_spend": round(total_if_typical, 2),
        "projected_savings_per_show": savings_per_show,
        "savings_pct": round((savings_per_show / total_if_typical) * 100, 1) if total_if_typical else 0,
    }

    if history_analysis:
        rec["historical_rush_cost_total"] = history_analysis["total_rush_cost"]
        rec["patterns"] = history_analysis["patterns"]

    return rec


# ---------------------------------------------------------------------------
# DEMO MODE
# ---------------------------------------------------------------------------

def generate_demo_history() -> List[Dict]:
    """
    Generate realistic historical order data for 6 past shows at a
    40,000 sq ft exhibition venue. Simulates typical over- and under-ordering.
    """
    shows = [
        "CES 2025 Pavilion", "SXSW Interactive Hall", "Art Basel South",
        "NAB Show Floor C", "Dreamforce Expo West", "Comic-Con Hall H",
    ]

    # For each item, define a realistic "actually used" qty for a 40k sqft,
    # 15 zone, 200 exhibit show — then simulate what was ordered vs. used.
    # over_bias > 1 means they tend to over-order; under means they run short.
    biases = {
        "tape_gaffer":        {"used": 35, "over_bias": 1.30, "rush_pct": 0.00},
        "tape_spike":         {"used": 48, "over_bias": 1.25, "rush_pct": 0.00},
        "tape_double_sided":  {"used": 32, "over_bias": 1.40, "rush_pct": 0.00},
        "tape_masking":       {"used": 15, "over_bias": 1.35, "rush_pct": 0.00},
        "screws_drywall":     {"used": 42, "over_bias": 1.20, "rush_pct": 0.05},
        "screws_wood":        {"used": 28, "over_bias": 1.15, "rush_pct": 0.05},
        "screws_machine":     {"used": 13, "over_bias": 1.10, "rush_pct": 0.08},
        "foam_protective":    {"used": 125, "over_bias": 1.30, "rush_pct": 0.00},
        "foam_padding":       {"used": 65, "over_bias": 1.30, "rush_pct": 0.00},
        "carts":              {"used": 4,  "over_bias": 1.50, "rush_pct": 0.00},
        "crates":             {"used": 52, "over_bias": 1.10, "rush_pct": 0.03},
        "cat6_cable":         {"used": 1100, "over_bias": 0.80, "rush_pct": 0.25},  # frequently under-ordered
        "paint_touchup":      {"used": 6,  "over_bias": 1.50, "rush_pct": 0.00},
        "zip_ties":           {"used": 22, "over_bias": 1.30, "rush_pct": 0.00},
        "velcro_strips":      {"used": 42, "over_bias": 1.20, "rush_pct": 0.05},
        "cable_management":   {"used": 32, "over_bias": 0.85, "rush_pct": 0.18},  # frequently under-ordered
        "batteries_aa":       {"used": 18, "over_bias": 1.25, "rush_pct": 0.05},
        "batteries_9v":       {"used": 8,  "over_bias": 1.20, "rush_pct": 0.08},
        "cleaning_general":   {"used": 7,  "over_bias": 1.40, "rush_pct": 0.00},
        "cleaning_glass":     {"used": 11, "over_bias": 1.35, "rush_pct": 0.00},
    }

    import random
    random.seed(42)  # reproducible demo data

    rows = []
    for show in shows:
        for iid, b in biases.items():
            # Vary usage +/-15% per show
            used = max(1, int(b["used"] * random.uniform(0.85, 1.15)))
            ordered = max(used, int(used * b["over_bias"] * random.uniform(0.95, 1.05)))
            rush_qty = int(used * b["rush_pct"] * random.uniform(0.5, 1.5)) if b["rush_pct"] > 0 else 0
            rush_cost = round(CONSUMABLES[iid]["bulk_price"] * CONSUMABLES[iid]["rush_markup"], 2) if rush_qty > 0 else 0.0

            rows.append({
                "show_name": show,
                "item_id": iid,
                "ordered_qty": ordered,
                "used_qty": used,
                "rush_qty": rush_qty,
                "rush_unit_cost": rush_cost,
            })

    return rows


def run_demo() -> Dict:
    """
    Full demo: calculate for a 40k sqft venue, compare against simulated
    historical data, and show projected savings.
    """
    # Venue parameters
    params = {
        "sqft": 40000,
        "zones": 15,
        "exhibits": 200,
        "venue_type": "convention_center",
        "complexity": "moderate",
        "condition": "good",
        "dock_distance_ft": 350,
    }

    calculated = calculate_quantities(**params)
    history = generate_demo_history()
    history_analysis = analyze_history(history)
    recommendation = build_recommendation(calculated, history_analysis)

    return {
        "mode": "demo",
        "venue_parameters": params,
        "calculated_quantities": {k: v for k, v in calculated.items()},
        "historical_analysis": history_analysis,
        "recommendation": recommendation,
        "generated_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# HTML REPORT GENERATION
# ---------------------------------------------------------------------------

def generate_html_report(data: Dict) -> str:
    """Generate a clean HTML report with the AUROS dark theme."""
    bg = "#08080c"
    gold = "#c9a84c"
    cream = "#f0ece4"

    params = data.get("venue_parameters", {})
    rec = data.get("recommendation", {})
    hist = data.get("historical_analysis", {})

    # Build order table rows
    order_rows = ""
    for line in rec.get("order_lines", []):
        order_rows += f"""
        <tr>
            <td>{line['label']}</td>
            <td style="text-align:center">{line['recommended_qty']}</td>
            <td style="text-align:center">{line['unit']}</td>
            <td style="text-align:center">{line['buffer_pct']}</td>
            <td style="text-align:right">${line['unit_cost']:.2f}</td>
            <td style="text-align:right">${line['line_total']:,.2f}</td>
        </tr>"""

    # Build historical analysis rows
    hist_rows = ""
    if hist.get("per_item"):
        for iid, a in hist["per_item"].items():
            over_class = ' class="warn"' if a["over_order_pct"] >= 20 else ""
            under_class = ' class="danger"' if a["under_order_pct"] >= 15 else ""
            hist_rows += f"""
        <tr>
            <td>{a['label']}</td>
            <td style="text-align:center">{a['total_ordered']}</td>
            <td style="text-align:center">{a['total_used']}</td>
            <td style="text-align:center"{over_class}>{a['over_order_pct']}%</td>
            <td style="text-align:center">{a['rush_qty']}</td>
            <td style="text-align:center"{under_class}>{a['under_order_pct']}%</td>
            <td style="text-align:right">${a['rush_cost']:,.2f}</td>
        </tr>"""

    hist_section = ""
    if hist_rows:
        patterns_html = ""
        for p in hist.get("patterns", []):
            patterns_html += f"<li>{p}</li>"

        hist_section = f"""
    <h2>Historical Analysis <span class="subtitle">({list(hist['per_item'].values())[0]['shows_analyzed'] if hist.get('per_item') else 0} shows)</span></h2>
    <table>
        <thead>
            <tr>
                <th>Item</th>
                <th>Total Ordered</th>
                <th>Total Used</th>
                <th>Over-Order %</th>
                <th>Rush Qty</th>
                <th>Under-Order %</th>
                <th>Rush Cost</th>
            </tr>
        </thead>
        <tbody>{hist_rows}
        </tbody>
    </table>
    <div class="rush-total">Total Rush Order Costs: <strong>${hist.get('total_rush_cost', 0):,.2f}</strong></div>

    <h3>Detected Patterns</h3>
    <ul class="patterns">{patterns_html}</ul>
    """

    savings_section = ""
    if rec.get("projected_savings_per_show", 0) > 0:
        savings_section = f"""
    <div class="savings-box">
        <h3>Projected Savings</h3>
        <div class="savings-grid">
            <div class="savings-item">
                <span class="savings-label">Optimized Cost (per show)</span>
                <span class="savings-value">${rec['total_bulk_cost']:,.2f}</span>
            </div>
            <div class="savings-item">
                <span class="savings-label">Typical Spend (per show)</span>
                <span class="savings-value" style="color:{cream}">${rec['estimated_typical_spend']:,.2f}</span>
            </div>
            <div class="savings-item highlight">
                <span class="savings-label">Savings Per Show</span>
                <span class="savings-value">${rec['projected_savings_per_show']:,.2f}</span>
            </div>
            <div class="savings-item highlight">
                <span class="savings-label">Savings %</span>
                <span class="savings-value">{rec['savings_pct']}%</span>
            </div>
        </div>
    </div>"""

    venue_type_label = params.get("venue_type", "N/A").replace("_", " ").title()

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AUROS AI — Consumables Order Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: {bg};
            color: {cream};
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            padding: 40px;
            line-height: 1.6;
        }}
        .header {{
            border-bottom: 2px solid {gold};
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: {gold};
            font-size: 28px;
            font-weight: 300;
            letter-spacing: 2px;
        }}
        .header .timestamp {{
            color: #888;
            font-size: 13px;
            margin-top: 4px;
        }}
        h2 {{
            color: {gold};
            font-size: 20px;
            font-weight: 400;
            margin: 30px 0 15px 0;
            letter-spacing: 1px;
        }}
        h2 .subtitle {{
            color: #888;
            font-size: 14px;
            font-weight: 300;
        }}
        h3 {{
            color: {gold};
            font-size: 16px;
            font-weight: 400;
            margin: 20px 0 10px 0;
        }}
        .venue-params {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 12px;
            margin-bottom: 30px;
        }}
        .param-card {{
            background: #111118;
            border: 1px solid #222;
            border-radius: 6px;
            padding: 14px 18px;
        }}
        .param-card .param-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
        }}
        .param-card .param-value {{
            font-size: 22px;
            color: {gold};
            font-weight: 300;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        th {{
            background: #111118;
            color: {gold};
            font-weight: 400;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 1px;
            padding: 12px 10px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        td {{
            padding: 10px;
            border-bottom: 1px solid #1a1a22;
            font-size: 14px;
        }}
        tr:hover td {{
            background: #111118;
        }}
        td.warn, td[class="warn"] {{
            color: #e6a817;
            font-weight: 600;
        }}
        td.danger, td[class="danger"] {{
            color: #e04040;
            font-weight: 600;
        }}
        .rush-total {{
            background: #1a1018;
            border: 1px solid #e04040;
            border-radius: 6px;
            padding: 14px 20px;
            font-size: 16px;
            color: #e04040;
            margin: 10px 0 20px 0;
        }}
        .patterns {{
            list-style: none;
            padding: 0;
        }}
        .patterns li {{
            background: #111118;
            border-left: 3px solid {gold};
            padding: 10px 16px;
            margin-bottom: 8px;
            border-radius: 0 4px 4px 0;
            font-size: 14px;
        }}
        .savings-box {{
            background: #0a1a0a;
            border: 1px solid #2a6a2a;
            border-radius: 8px;
            padding: 24px;
            margin: 20px 0;
        }}
        .savings-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 16px;
        }}
        .savings-item {{
            text-align: center;
        }}
        .savings-item .savings-label {{
            display: block;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #888;
            margin-bottom: 4px;
        }}
        .savings-item .savings-value {{
            font-size: 28px;
            font-weight: 300;
            color: {cream};
        }}
        .savings-item.highlight .savings-value {{
            color: #4CAF50;
            font-weight: 400;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #222;
            font-size: 12px;
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AUROS AI &mdash; Consumables Order Report</h1>
        <div class="timestamp">Generated {data.get('generated_at', datetime.now().isoformat())}</div>
    </div>

    <h2>Venue Parameters</h2>
    <div class="venue-params">
        <div class="param-card">
            <div class="param-label">Square Footage</div>
            <div class="param-value">{params.get('sqft', 0):,}</div>
        </div>
        <div class="param-card">
            <div class="param-label">Rooms / Zones</div>
            <div class="param-value">{params.get('zones', 0)}</div>
        </div>
        <div class="param-card">
            <div class="param-label">Exhibit Pieces</div>
            <div class="param-value">{params.get('exhibits', 0)}</div>
        </div>
        <div class="param-card">
            <div class="param-label">Venue Type</div>
            <div class="param-value" style="font-size:16px">{venue_type_label}</div>
        </div>
        <div class="param-card">
            <div class="param-label">Layout Complexity</div>
            <div class="param-value" style="font-size:16px">{params.get('complexity', 'moderate').title()}</div>
        </div>
        <div class="param-card">
            <div class="param-label">Venue Condition</div>
            <div class="param-value" style="font-size:16px">{params.get('condition', 'good').replace('_', ' ').title()}</div>
        </div>
        <div class="param-card">
            <div class="param-label">Dock Distance</div>
            <div class="param-value">{params.get('dock_distance_ft', 200)} ft</div>
        </div>
    </div>

    <h2>Order Recommendation</h2>
    <table>
        <thead>
            <tr>
                <th>Item</th>
                <th>Qty</th>
                <th>Unit</th>
                <th>Buffer</th>
                <th>Unit Cost</th>
                <th>Line Total</th>
            </tr>
        </thead>
        <tbody>{order_rows}
        </tbody>
    </table>
    <div style="text-align:right; font-size:18px; color:{gold}; margin-bottom:10px;">
        Total: <strong>${rec.get('total_bulk_cost', 0):,.2f}</strong>
    </div>

    {savings_section}

    {hist_section}

    <div class="footer">
        AUROS AI Consumables Calculator &bull; Formulas calibrated for live entertainment production &bull; Buffer recommendations based on industry benchmarks
    </div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AUROS AI — Consumables Calculator for Live Entertainment Production",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python consumables_calculator.py --demo
  python consumables_calculator.py --sqft 40000 --zones 15 --exhibits 200 --type convention_center
  python consumables_calculator.py --sqft 40000 --zones 15 --exhibits 200 --history past_orders.csv
        """,
    )

    parser.add_argument("--demo", action="store_true", help="Run demo with realistic data for a 40,000 sq ft exhibition venue")
    parser.add_argument("--sqft", type=int, help="Venue square footage")
    parser.add_argument("--zones", type=int, help="Number of rooms/zones")
    parser.add_argument("--exhibits", type=int, help="Number of exhibit pieces")
    parser.add_argument("--type", dest="venue_type", default="convention_center",
                        choices=["convention_center", "museum", "warehouse", "theater"],
                        help="Venue type (default: convention_center)")
    parser.add_argument("--complexity", default="moderate",
                        choices=["simple", "moderate", "complex"],
                        help="Layout complexity (default: moderate)")
    parser.add_argument("--condition", default="good",
                        choices=["new", "good", "needs_work"],
                        help="Venue condition (default: good)")
    parser.add_argument("--dock-distance", type=int, default=200,
                        help="Distance from loading dock to install areas in feet (default: 200)")
    parser.add_argument("--history", type=str, help="Path to CSV of past orders for comparison")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only, no HTML")
    parser.add_argument("--output-dir", type=str, default=".", help="Directory for output files")

    args = parser.parse_args()

    # --- Demo mode ---
    if args.demo:
        print("=" * 60)
        print("  AUROS AI — Consumables Calculator")
        print("  DEMO MODE: 40,000 sq ft exhibition venue")
        print("=" * 60)
        print()

        data = run_demo()

        # Write JSON
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, "consumables_report.json")
        with open(json_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  JSON report: {json_path}")

        # Write HTML
        if not args.json_only:
            html = generate_html_report(data)
            html_path = os.path.join(output_dir, "consumables_report.html")
            with open(html_path, "w") as f:
                f.write(html)
            print(f"  HTML report: {html_path}")

        print()

        # Print summary to console
        rec = data["recommendation"]
        hist = data["historical_analysis"]

        print(f"  Optimized order total:   ${rec['total_bulk_cost']:>10,.2f}")
        print(f"  Typical spend (est.):    ${rec['estimated_typical_spend']:>10,.2f}")
        print(f"  Savings per show:        ${rec['projected_savings_per_show']:>10,.2f}  ({rec['savings_pct']}%)")
        print(f"  Rush fees (6 shows):     ${hist['total_rush_cost']:>10,.2f}")
        print()

        if hist["patterns"]:
            print("  Detected patterns:")
            for p in hist["patterns"]:
                print(f"    - {p}")
            print()

        print("  Order breakdown:")
        print(f"  {'Item':<35} {'Qty':>6}  {'Unit':<18} {'Cost':>10}")
        print("  " + "-" * 75)
        for line in rec["order_lines"]:
            print(f"  {line['label']:<35} {line['recommended_qty']:>6}  {line['unit']:<18} ${line['line_total']:>9,.2f}")
        print("  " + "-" * 75)
        print(f"  {'TOTAL':<35} {'':>6}  {'':>18} ${rec['total_bulk_cost']:>9,.2f}")
        print()
        return

    # --- Standard calculation mode ---
    if not args.sqft or not args.zones or not args.exhibits:
        parser.error("--sqft, --zones, and --exhibits are required (or use --demo)")

    params = {
        "sqft": args.sqft,
        "zones": args.zones,
        "exhibits": args.exhibits,
        "venue_type": args.venue_type,
        "complexity": args.complexity,
        "condition": args.condition,
        "dock_distance_ft": args.dock_distance,
    }

    print("=" * 60)
    print("  AUROS AI — Consumables Calculator")
    print(f"  {args.sqft:,} sq ft | {args.zones} zones | {args.exhibits} exhibits")
    print(f"  {args.venue_type.replace('_', ' ').title()} | {args.complexity.title()} | {args.condition.replace('_', ' ').title()}")
    print("=" * 60)
    print()

    calculated = calculate_quantities(**params)

    # Historical comparison
    history_analysis = None
    if args.history:
        if not os.path.exists(args.history):
            print(f"  WARNING: History file not found: {args.history}")
            print("  Proceeding without historical comparison.")
            print()
        else:
            history = load_history(args.history)
            history_analysis = analyze_history(history)

    recommendation = build_recommendation(calculated, history_analysis)

    data = {
        "mode": "calculation",
        "venue_parameters": params,
        "calculated_quantities": calculated,
        "recommendation": recommendation,
        "generated_at": datetime.now().isoformat(),
    }

    if history_analysis:
        data["historical_analysis"] = history_analysis

    # Write JSON
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, "consumables_report.json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  JSON report: {json_path}")

    # Write HTML
    if not args.json_only:
        html = generate_html_report(data)
        html_path = os.path.join(output_dir, "consumables_report.html")
        with open(html_path, "w") as f:
            f.write(html)
        print(f"  HTML report: {html_path}")

    print()

    # Console summary
    rec = recommendation
    print(f"  Optimized order total:   ${rec['total_bulk_cost']:>10,.2f}")
    print(f"  Typical spend (est.):    ${rec['estimated_typical_spend']:>10,.2f}")
    print(f"  Savings per show:        ${rec['projected_savings_per_show']:>10,.2f}  ({rec['savings_pct']}%)")
    print()

    if history_analysis:
        print(f"  Rush fees (historical):  ${history_analysis['total_rush_cost']:>10,.2f}")
        if history_analysis["patterns"]:
            print()
            print("  Detected patterns:")
            for p in history_analysis["patterns"]:
                print(f"    - {p}")
        print()

    print("  Order breakdown:")
    print(f"  {'Item':<35} {'Qty':>6}  {'Unit':<18} {'Cost':>10}")
    print("  " + "-" * 75)
    for line in rec["order_lines"]:
        print(f"  {line['label']:<35} {line['recommended_qty']:>6}  {line['unit']:<18} ${line['line_total']:>9,.2f}")
    print("  " + "-" * 75)
    print(f"  {'TOTAL':<35} {'':>6}  {'':>18} ${rec['total_bulk_cost']:>9,.2f}")
    print()


if __name__ == "__main__":
    main()
