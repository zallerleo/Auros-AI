#!/usr/bin/env python3
"""
AUROS AI — Install Cost Analyzer
Analyzes production install costs for live entertainment companies
(exhibitions, concerts, touring shows) and identifies waste, inefficiencies,
and actionable savings.

Usage:
    python tools/install_analyzer.py --demo                          # Demo with sample data
    python tools/install_analyzer.py --demo --output report.html     # Export HTML report
    python tools/install_analyzer.py --data install_data.csv         # Analyze real data
    python tools/install_analyzer.py --data install_data.csv --ai    # With AI recommendations
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Ensure project root is on sys.path ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Optional imports (graceful degradation) ─────────────────────────────────
try:
    from agents.shared.config import PROJECT_ROOT as _PR
    PROJECT_ROOT = _PR
except ImportError:
    pass

try:
    from agents.shared.llm import generate as llm_generate
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

try:
    import openpyxl  # noqa: F401 — used implicitly for xlsx reading
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ═══════════════════════════════════════════════════════════════════════════════
#  COST CATEGORY DEFINITIONS & BENCHMARKS
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORIES = [
    "consumables",
    "transportation",
    "rush_orders",
    "labor",
    "equipment_rentals",
    "vendor_contractor",
    "venue_specific",
]

# Industry benchmarks: optimal spend as a percentage of typical actual spend.
# These represent what well-optimized operations achieve.
BENCHMARKS = {
    "consumables":       {"optimal_ratio": 0.82, "label": "Consumables"},
    "transportation":    {"optimal_ratio": 0.78, "label": "Transportation"},
    "rush_orders":       {"optimal_ratio": 0.40, "label": "Rush Orders"},
    "labor":             {"optimal_ratio": 0.88, "label": "Labor (Install Crew)"},
    "equipment_rentals": {"optimal_ratio": 0.85, "label": "Equipment Rentals"},
    "vendor_contractor": {"optimal_ratio": 0.90, "label": "Vendor / Contractor"},
    "venue_specific":    {"optimal_ratio": 0.92, "label": "Venue-Specific Costs"},
}


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class LineItem:
    """A single cost line item."""
    def __init__(
        self,
        category: str,
        subcategory: str,
        description: str,
        quantity: float,
        unit_cost: float,
        actual_total: float | None = None,
        optimal_unit_cost: float | None = None,
        notes: str = "",
    ):
        self.category = category
        self.subcategory = subcategory
        self.description = description
        self.quantity = quantity
        self.unit_cost = unit_cost
        self.actual_total = actual_total if actual_total is not None else quantity * unit_cost
        self.optimal_unit_cost = optimal_unit_cost
        self.notes = notes

    @property
    def optimal_total(self) -> float:
        if self.optimal_unit_cost is not None:
            return self.quantity * self.optimal_unit_cost
        ratio = BENCHMARKS.get(self.category, {}).get("optimal_ratio", 0.85)
        return self.actual_total * ratio

    @property
    def waste(self) -> float:
        return self.actual_total - self.optimal_total

    @property
    def waste_pct(self) -> float:
        return (self.waste / self.actual_total * 100) if self.actual_total else 0.0

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "description": self.description,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "actual_total": round(self.actual_total, 2),
            "optimal_total": round(self.optimal_total, 2),
            "waste": round(self.waste, 2),
            "waste_pct": round(self.waste_pct, 1),
            "notes": self.notes,
        }


class CategorySummary:
    """Aggregated summary for one cost category."""
    def __init__(self, category: str, items: list[LineItem]):
        self.category = category
        self.label = BENCHMARKS.get(category, {}).get("label", category.title())
        self.items = items
        self.total_spend = sum(i.actual_total for i in items)
        self.optimal_spend = sum(i.optimal_total for i in items)
        self.waste = self.total_spend - self.optimal_spend
        self.waste_pct = (self.waste / self.total_spend * 100) if self.total_spend else 0.0
        self.waste_drivers = self._identify_waste_drivers()

    def _identify_waste_drivers(self) -> list[str]:
        drivers = []
        sorted_items = sorted(self.items, key=lambda i: i.waste, reverse=True)
        for item in sorted_items[:5]:
            if item.waste > 0:
                if item.notes:
                    drivers.append(f"{item.description}: ${item.waste:,.0f} waste — {item.notes}")
                else:
                    drivers.append(
                        f"{item.description}: ${item.waste:,.0f} over optimal "
                        f"({item.waste_pct:.0f}% above benchmark)"
                    )
        return drivers

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "label": self.label,
            "total_spend": round(self.total_spend, 2),
            "optimal_spend": round(self.optimal_spend, 2),
            "waste": round(self.waste, 2),
            "waste_pct": round(self.waste_pct, 1),
            "waste_drivers": self.waste_drivers,
            "line_items": [i.to_dict() for i in self.items],
        }


class InstallReport:
    """Full install cost analysis report."""
    def __init__(
        self,
        show_name: str,
        venue: str,
        install_date: str,
        categories: list[CategorySummary],
        moves_per_year: int = 2,
        ai_analysis: str | None = None,
    ):
        self.show_name = show_name
        self.venue = venue
        self.install_date = install_date
        self.categories = categories
        self.moves_per_year = moves_per_year
        self.ai_analysis = ai_analysis

        self.total_cost = sum(c.total_spend for c in categories)
        self.total_optimal = sum(c.optimal_spend for c in categories)
        self.total_waste = self.total_cost - self.total_optimal
        self.waste_pct = (self.total_waste / self.total_cost * 100) if self.total_cost else 0.0
        self.annual_savings = self.total_waste * moves_per_year

        # Top 5 waste areas
        all_items: list[LineItem] = []
        for c in categories:
            all_items.extend(c.items)
        all_items.sort(key=lambda i: i.waste, reverse=True)
        self.top_waste_items = all_items[:5]

        self.recommendations = self._generate_recommendations()

    def _generate_recommendations(self) -> list[str]:
        recs = []
        cat_waste = sorted(self.categories, key=lambda c: c.waste, reverse=True)
        for c in cat_waste:
            if c.waste <= 0:
                continue
            if c.category == "rush_orders":
                recs.append(
                    f"RUSH ORDERS: Eliminate ${c.waste:,.0f} in markup by pre-ordering "
                    f"consumables 3-4 weeks before each move. Maintain a rolling inventory "
                    f"of high-turnover items (tape, cable, foam, hardware)."
                )
            elif c.category == "transportation":
                recs.append(
                    f"TRANSPORTATION: Optimize truck loading to save ${c.waste:,.0f}. "
                    f"Use load planning software to maximize cubic utilization. "
                    f"Consolidate partial loads and eliminate deadhead runs."
                )
            elif c.category == "consumables":
                recs.append(
                    f"CONSUMABLES: Reduce waste by ${c.waste:,.0f} through standardized "
                    f"kitting, per-department allocation tracking, and bulk purchasing "
                    f"agreements with 2-3 preferred vendors."
                )
            elif c.category == "labor":
                recs.append(
                    f"LABOR: Save ${c.waste:,.0f} by optimizing crew scheduling. "
                    f"Stagger call times by department, reduce overtime through better "
                    f"advance planning, and cross-train crew to reduce idle time."
                )
            elif c.category == "equipment_rentals":
                recs.append(
                    f"EQUIPMENT RENTALS: Save ${c.waste:,.0f} by negotiating annual "
                    f"rental agreements, purchasing frequently-rented items, and "
                    f"coordinating rental periods to avoid overlap charges."
                )
            elif c.category == "vendor_contractor":
                recs.append(
                    f"VENDORS: Save ${c.waste:,.0f} by rebidding contracts annually, "
                    f"bundling services, and establishing preferred vendor programs "
                    f"with volume commitments."
                )
            elif c.category == "venue_specific":
                recs.append(
                    f"VENUE COSTS: Save ${c.waste:,.0f} by negotiating venue packages "
                    f"upfront, sharing rigging/power infrastructure across departments, "
                    f"and advance-permitting to avoid rush fees."
                )
        return recs

    def to_dict(self) -> dict:
        return {
            "report_generated": datetime.now().isoformat(),
            "show_name": self.show_name,
            "venue": self.venue,
            "install_date": self.install_date,
            "moves_per_year": self.moves_per_year,
            "summary": {
                "total_install_cost": round(self.total_cost, 2),
                "optimal_cost": round(self.total_optimal, 2),
                "total_identified_waste": round(self.total_waste, 2),
                "waste_percentage": round(self.waste_pct, 1),
                "projected_annual_savings": round(self.annual_savings, 2),
            },
            "top_5_waste_areas": [
                {
                    "description": i.description,
                    "category": i.category,
                    "waste_amount": round(i.waste, 2),
                    "notes": i.notes,
                }
                for i in self.top_waste_items
            ],
            "recommendations": self.recommendations,
            "categories": [c.to_dict() for c in self.categories],
            "ai_analysis": self.ai_analysis,
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  DEMO DATA GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_demo_data() -> tuple[dict[str, Any], list[LineItem]]:
    """
    Generate realistic demo data for a large touring exhibition.
    Based on real-world cost patterns for a 40-truck exhibition show move.
    """
    meta = {
        "show_name": "Immersive Worlds: The Exhibition",
        "venue": "McCormick Place, Chicago — Halls F1-F3",
        "install_date": "2026-03-15",
        "moves_per_year": 2,
    }

    items: list[LineItem] = []

    # ── TRANSPORTATION ──────────────────────────────────────────────────────
    items.extend([
        LineItem("transportation", "trucking", "53' trailers — full show move (32 trucks)",
                 32, 2650.00, notes="Avg 82% capacity — 6 trucks under 60%"),
        LineItem("transportation", "trucking", "53' trailers — overflow/late add (5 trucks)",
                 5, 3100.00, notes="Booked 10 days late, premium rate. 3 trucks at <50% capacity"),
        LineItem("transportation", "trucking", "Specialty flatbeds — oversized scenic (3 trucks)",
                 3, 4200.00, notes="Required for scenic arches; 1 truck only 35% loaded"),
        LineItem("transportation", "fuel_surcharge", "Fuel surcharge — all vehicles",
                 1, 8400.00),
        LineItem("transportation", "driver_costs", "Driver per diem & lodging (40 drivers x 3 days)",
                 120, 185.00, optimal_unit_cost=165.00,
                 notes="No preferred hotel rate negotiated"),
        LineItem("transportation", "deadhead", "Deadhead return — empty trucks to depot",
                 8, 1100.00, optimal_unit_cost=0.0,
                 notes="8 trucks returned empty — could backhaul or consolidate"),
    ])

    # ── CONSUMABLES ─────────────────────────────────────────────────────────
    items.extend([
        LineItem("consumables", "tape", "Gaffer tape (2\" black, 60yd) — 480 rolls",
                 480, 14.50, optimal_unit_cost=11.20,
                 notes="Purchased per-roll from local supplier; bulk price is $11.20"),
        LineItem("consumables", "tape", "Spike tape (assorted colors) — 200 rolls",
                 200, 8.75, optimal_unit_cost=5.90,
                 notes="Show-branded colors ordered rush from specialty vendor"),
        LineItem("consumables", "cable", "Cat-6 cable (1000ft boxes) — 24 boxes",
                 24, 189.00, optimal_unit_cost=142.00,
                 notes="Same cable bought bulk last year at $142/box"),
        LineItem("consumables", "cable", "Cat-6 patch cables (assorted lengths) — 300 pcs",
                 300, 7.50, optimal_unit_cost=4.80,
                 notes="Pre-made vs. making on-site with bulk cable"),
        LineItem("consumables", "hardware", "Screws, bolts, anchors — assorted hardware kits",
                 1, 4800.00, optimal_unit_cost=3200.00,
                 notes="Over-ordered by ~30%; leftover hardware not inventoried for reuse"),
        LineItem("consumables", "foam", "Polyethylene foam sheets (4'x8'x2\")",
                 180, 42.00, optimal_unit_cost=28.50,
                 notes="Rush order from local plastics supplier at 47% markup"),
        LineItem("consumables", "paint", "Touch-up paint (custom match, gallons)",
                 35, 145.00, optimal_unit_cost=89.00,
                 notes="Custom color match on-site; could be pre-mixed from scenic shop"),
        LineItem("consumables", "fabric", "Duvetyne (bolt, 54\" wide, 50yd)",
                 28, 285.00, optimal_unit_cost=195.00,
                 notes="Flame-retardant fabric bought retail; wholesale is $195/bolt"),
        LineItem("consumables", "carts", "Heavy-duty utility carts",
                 15, 189.00, optimal_unit_cost=0.0,
                 notes="Purchased new each move; should be company-owned rolling stock"),
        LineItem("consumables", "crates", "Custom ATA road cases — replacement",
                 8, 650.00, optimal_unit_cost=420.00,
                 notes="Cases damaged in transit — preventable with better load planning"),
        LineItem("consumables", "misc", "Zip ties, velcro, markers, labels, misc supplies",
                 1, 3200.00, optimal_unit_cost=2100.00,
                 notes="No standardized kit; departments over-order independently"),
        LineItem("consumables", "expendables", "Batteries, lamps, fuses, gel — expendable stock",
                 1, 8900.00, optimal_unit_cost=6500.00,
                 notes="No tracking system; departments hoard and re-order"),
    ])

    # ── RUSH ORDERS ─────────────────────────────────────────────────────────
    items.extend([
        LineItem("rush_orders", "foam", "Emergency foam order — local supplier",
                 60, 58.00, optimal_unit_cost=28.50,
                 notes="Ran out during install; local supplier charged 103% markup over bulk"),
        LineItem("rush_orders", "hardware", "Same-day hardware store run (x4 trips)",
                 4, 1850.00, optimal_unit_cost=680.00,
                 notes="Missing fasteners, brackets; retail markup + crew time for pickup"),
        LineItem("rush_orders", "cable", "Emergency cable order — overnight shipping",
                 12, 340.00, optimal_unit_cost=142.00,
                 notes="Cat-6 boxes — ran short, overnight from B&H at $340 vs. $142 bulk"),
        LineItem("rush_orders", "paint", "Rush scenic touch-up supplies",
                 1, 2800.00, optimal_unit_cost=950.00,
                 notes="Local scenic shop emergency order — 3x standard cost"),
        LineItem("rush_orders", "tools", "Replacement tools (lost/broken during install)",
                 1, 3400.00, optimal_unit_cost=1200.00,
                 notes="No tool tracking system; buying retail at Home Depot"),
        LineItem("rush_orders", "electrical", "Emergency electrical supplies (breakers, wire, connectors)",
                 1, 4200.00, optimal_unit_cost=1800.00,
                 notes="Venue power config different from advance; emergency purchases"),
        LineItem("rush_orders", "shipping", "Rush/overnight shipping charges (all emergency orders)",
                 1, 6800.00, optimal_unit_cost=0.0,
                 notes="100% avoidable with proper advance ordering"),
    ])

    # ── LABOR ───────────────────────────────────────────────────────────────
    items.extend([
        LineItem("labor", "install_crew", "Install technicians — straight time (32 crew x 10hr x 5 days)",
                 1600, 38.00, notes="Base install crew — standard rate"),
        LineItem("labor", "install_crew", "Install technicians — overtime (32 crew x avg 3hr OT x 5 days)",
                 480, 57.00, optimal_unit_cost=38.00,
                 notes="$9,120 in OT premium — schedule overrun from late truck arrivals"),
        LineItem("labor", "department_heads", "Department heads / leads (8 x 12hr x 6 days)",
                 576, 62.00),
        LineItem("labor", "department_heads", "Department heads — overtime premium",
                 96, 93.00, optimal_unit_cost=62.00,
                 notes="$2,976 OT premium — caused by scope changes during install"),
        LineItem("labor", "specialty", "Specialty technicians (AV, lighting, automation)",
                 12, 850.00, notes="Day rate — specialty skills"),
        LineItem("labor", "riggers", "Certified riggers (union, 6 x 10hr x 4 days)",
                 240, 72.00),
        LineItem("labor", "riggers", "Rigger overtime",
                 48, 108.00, optimal_unit_cost=72.00,
                 notes="$1,728 OT premium — rigging delayed by venue access issues"),
        LineItem("labor", "stagehands", "Local stagehands (IATSE call, 20 x 10hr x 3 days)",
                 600, 45.00, notes="Standard local call"),
        LineItem("labor", "idle_time", "Crew idle time — waiting on deliveries/access",
                 1, 8500.00, optimal_unit_cost=0.0,
                 notes="Estimated 220 crew-hours lost to waiting; 100% avoidable"),
        LineItem("labor", "supervision", "Production management / supervision",
                 1, 18000.00, notes="PM team for install week"),
    ])

    # ── EQUIPMENT RENTALS ───────────────────────────────────────────────────
    items.extend([
        LineItem("equipment_rentals", "lifts", "Scissor lifts (6 units x 7 days)",
                 42, 285.00, optimal_unit_cost=210.00,
                 notes="Daily rate; weekly rate would save 26%"),
        LineItem("equipment_rentals", "lifts", "Boom lifts (4 units x 5 days)",
                 20, 425.00, optimal_unit_cost=340.00,
                 notes="No volume discount negotiated"),
        LineItem("equipment_rentals", "forklifts", "Forklifts (3 units x 6 days)",
                 18, 350.00, optimal_unit_cost=275.00,
                 notes="Rented from venue at premium; outside vendor is cheaper"),
        LineItem("equipment_rentals", "scaffolding", "Scaffolding package",
                 1, 14500.00, optimal_unit_cost=11000.00,
                 notes="Venue-exclusive vendor; no competitive bid"),
        LineItem("equipment_rentals", "power_distro", "Temporary power distribution",
                 1, 8200.00, optimal_unit_cost=6500.00,
                 notes="Could be company-owned for shows with 2+ moves/year"),
        LineItem("equipment_rentals", "comms", "Radio/comms rental (50 units x 7 days)",
                 350, 12.00, optimal_unit_cost=8.00,
                 notes="Renting vs. owning; breakeven at 4 events/year"),
    ])

    # ── VENDOR / CONTRACTOR ─────────────────────────────────────────────────
    items.extend([
        LineItem("vendor_contractor", "scenic", "Scenic installation contractor",
                 1, 32000.00, optimal_unit_cost=28000.00,
                 notes="Single-source; no competitive bid in 2 years"),
        LineItem("vendor_contractor", "av", "AV systems integration",
                 1, 28000.00, optimal_unit_cost=25000.00,
                 notes="Scope creep added $3K during install"),
        LineItem("vendor_contractor", "electrical", "Electrical contractor (venue-required)",
                 1, 22000.00, optimal_unit_cost=22000.00,
                 notes="Venue-mandated contractor — limited negotiation"),
        LineItem("vendor_contractor", "graphics", "Large-format graphics installation",
                 1, 15000.00, optimal_unit_cost=12500.00,
                 notes="Re-prints on-site due to damage in transit: $2,500"),
        LineItem("vendor_contractor", "flooring", "Flooring installation",
                 1, 18000.00, optimal_unit_cost=16000.00,
                 notes="Overtime charges from late venue access"),
    ])

    # ── VENUE-SPECIFIC ──────────────────────────────────────────────────────
    items.extend([
        LineItem("venue_specific", "rigging", "Venue rigging — motor points (48 points)",
                 48, 425.00, optimal_unit_cost=350.00,
                 notes="McCormick premium rate; advance booking saves 18%"),
        LineItem("venue_specific", "power", "Venue power — 1200A 3-phase service",
                 1, 16500.00, optimal_unit_cost=14000.00,
                 notes="Rush power order; standard advance rate is $14K"),
        LineItem("venue_specific", "internet", "Dedicated internet (1Gbps, 7 days)",
                 1, 8500.00, optimal_unit_cost=5500.00,
                 notes="Venue exclusive provider; no outside ISP allowed"),
        LineItem("venue_specific", "permits", "City permits & fire marshal inspection",
                 1, 3200.00, notes="Standard — non-negotiable"),
        LineItem("venue_specific", "drayage", "Venue drayage / material handling",
                 1, 12000.00, optimal_unit_cost=9500.00,
                 notes="Could reduce with better truck scheduling to avoid peak dock times"),
        LineItem("venue_specific", "cleaning", "Post-install cleaning / trash removal",
                 1, 4800.00, optimal_unit_cost=3200.00,
                 notes="Excessive debris from over-ordered consumables"),
        LineItem("venue_specific", "security", "24hr security during install (7 days)",
                 1, 9800.00, optimal_unit_cost=7500.00,
                 notes="Venue-mandated provider; rate above market"),
    ])

    return meta, items


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA LOADING — CSV / EXCEL
# ═══════════════════════════════════════════════════════════════════════════════

REQUIRED_COLUMNS = {"category", "subcategory", "description", "quantity", "unit_cost"}

def load_csv(path: str | Path) -> tuple[dict[str, Any], list[LineItem]]:
    """Load install data from a CSV file.

    Expected columns:
        category, subcategory, description, quantity, unit_cost,
        actual_total (opt), optimal_unit_cost (opt), notes (opt)
    Metadata rows: lines starting with '#' are parsed as key=value pairs.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    meta: dict[str, Any] = {
        "show_name": "Unknown Show",
        "venue": "Unknown Venue",
        "install_date": datetime.now().strftime("%Y-%m-%d"),
        "moves_per_year": 2,
    }
    items: list[LineItem] = []

    with open(path, newline="", encoding="utf-8-sig") as f:
        # Read metadata from comment lines
        lines = f.readlines()

    data_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            parts = stripped.lstrip("# ").split("=", 1)
            if len(parts) == 2:
                key, val = parts[0].strip().lower(), parts[1].strip()
                if key in meta:
                    meta[key] = int(val) if key == "moves_per_year" else val
        elif stripped:
            data_lines.append(stripped)

    if not data_lines:
        raise ValueError("No data rows found in CSV file")

    reader = csv.DictReader(data_lines)
    fields = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS - fields
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    for row in reader:
        try:
            item = LineItem(
                category=row["category"].strip().lower().replace(" ", "_"),
                subcategory=row.get("subcategory", "").strip(),
                description=row["description"].strip(),
                quantity=float(row["quantity"]),
                unit_cost=float(row["unit_cost"]),
                actual_total=float(row["actual_total"]) if row.get("actual_total") else None,
                optimal_unit_cost=float(row["optimal_unit_cost"]) if row.get("optimal_unit_cost") else None,
                notes=row.get("notes", "").strip(),
            )
            items.append(item)
        except (ValueError, KeyError) as e:
            print(f"  [WARN] Skipping row: {e}")

    return meta, items


def load_excel(path: str | Path) -> tuple[dict[str, Any], list[LineItem]]:
    """Load install data from an Excel file (.xlsx)."""
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl required for Excel files: pip install openpyxl")

    import openpyxl
    path = Path(path)
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    meta: dict[str, Any] = {
        "show_name": "Unknown Show",
        "venue": "Unknown Venue",
        "install_date": datetime.now().strftime("%Y-%m-%d"),
        "moves_per_year": 2,
    }
    items: list[LineItem] = []

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel file is empty")

    # Find header row
    header_idx = None
    for i, row in enumerate(rows):
        cells = [str(c).strip().lower() if c else "" for c in row]
        if "category" in cells and "description" in cells:
            header_idx = i
            break
        # Check for metadata
        first = str(row[0]).strip() if row[0] else ""
        if first.startswith("#"):
            parts = first.lstrip("# ").split("=", 1)
            if len(parts) == 2:
                key, val = parts[0].strip().lower(), parts[1].strip()
                if key in meta:
                    meta[key] = int(val) if key == "moves_per_year" else val

    if header_idx is None:
        raise ValueError("Could not find header row with 'category' and 'description' columns")

    headers = [str(c).strip().lower().replace(" ", "_") if c else f"col_{j}"
               for j, c in enumerate(rows[header_idx])]

    for row in rows[header_idx + 1:]:
        rd = {headers[j]: row[j] for j in range(min(len(headers), len(row)))}
        if not rd.get("category") or not rd.get("description"):
            continue
        try:
            item = LineItem(
                category=str(rd["category"]).strip().lower().replace(" ", "_"),
                subcategory=str(rd.get("subcategory", "")).strip(),
                description=str(rd["description"]).strip(),
                quantity=float(rd.get("quantity", 1)),
                unit_cost=float(rd.get("unit_cost", 0)),
                actual_total=float(rd["actual_total"]) if rd.get("actual_total") else None,
                optimal_unit_cost=float(rd["optimal_unit_cost"]) if rd.get("optimal_unit_cost") else None,
                notes=str(rd.get("notes", "")).strip(),
            )
            items.append(item)
        except (ValueError, KeyError) as e:
            print(f"  [WARN] Skipping row: {e}")

    wb.close()
    return meta, items


def load_data(path: str | Path) -> tuple[dict[str, Any], list[LineItem]]:
    """Load data from CSV or Excel based on file extension."""
    path = Path(path)
    ext = path.suffix.lower()
    if ext in (".xlsx", ".xls"):
        return load_excel(path)
    elif ext == ".csv":
        return load_csv(path)
    else:
        # Try CSV
        return load_csv(path)


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def analyze(
    meta: dict[str, Any],
    items: list[LineItem],
    use_ai: bool = False,
) -> InstallReport:
    """Run the full cost analysis and generate an InstallReport."""
    # Group items by category
    by_cat: dict[str, list[LineItem]] = {}
    for item in items:
        by_cat.setdefault(item.category, []).append(item)

    summaries = []
    for cat in CATEGORIES:
        if cat in by_cat:
            summaries.append(CategorySummary(cat, by_cat[cat]))
    # Include any categories not in the standard list
    for cat, cat_items in by_cat.items():
        if cat not in CATEGORIES:
            summaries.append(CategorySummary(cat, cat_items))

    ai_analysis = None
    if use_ai and HAS_LLM:
        ai_analysis = _run_ai_analysis(meta, summaries)

    return InstallReport(
        show_name=meta.get("show_name", "Unknown Show"),
        venue=meta.get("venue", "Unknown Venue"),
        install_date=meta.get("install_date", ""),
        categories=summaries,
        moves_per_year=int(meta.get("moves_per_year", 2)),
        ai_analysis=ai_analysis,
    )


def _run_ai_analysis(meta: dict, summaries: list[CategorySummary]) -> str:
    """Use Claude to generate deeper analysis and recommendations."""
    data_summary = json.dumps(
        {
            "show": meta.get("show_name"),
            "venue": meta.get("venue"),
            "categories": [
                {
                    "name": s.label,
                    "spend": round(s.total_spend),
                    "waste": round(s.waste),
                    "waste_pct": round(s.waste_pct, 1),
                    "top_drivers": s.waste_drivers[:3],
                }
                for s in summaries
            ],
            "total_spend": round(sum(s.total_spend for s in summaries)),
            "total_waste": round(sum(s.waste for s in summaries)),
        },
        indent=2,
    )

    prompt = f"""You are a production logistics and cost optimization expert for live entertainment
(touring exhibitions, concerts, theatrical productions).

Analyze this install cost data and provide:
1. Executive summary (3-4 sentences — make it hit hard)
2. Three highest-impact recommendations with specific dollar savings
3. Quick wins (things that can be fixed before the next move)
4. Systemic issues that need process changes
5. A 90-day action plan

Be specific. Use the actual numbers. This report goes to the COO.

Install Cost Data:
{data_summary}"""

    system = """You are a senior production operations consultant specializing in live entertainment
logistics and cost optimization. You've managed load-outs and installs for Cirque du Soleil,
touring Broadway shows, and major museum exhibitions. Be direct, specific, and data-driven.
No filler. Every recommendation must include a dollar figure."""

    try:
        return llm_generate(prompt, system=system, max_tokens=2000, temperature=0.4)
    except Exception as e:
        return f"[AI analysis unavailable: {e}]"


# ═══════════════════════════════════════════════════════════════════════════════
#  OUTPUT: TERMINAL
# ═══════════════════════════════════════════════════════════════════════════════

def _fmt(n: float) -> str:
    """Format a number as currency."""
    return f"${n:,.0f}"


def print_terminal_report(report: InstallReport) -> None:
    """Print a formatted summary to the terminal."""
    W = 72
    gold = "\033[33m"
    red = "\033[91m"
    green = "\033[92m"
    dim = "\033[90m"
    bold = "\033[1m"
    reset = "\033[0m"

    def hr(char="─"):
        print(f"{dim}{char * W}{reset}")

    print()
    hr("═")
    print(f"{bold}{gold}  AUROS AI — INSTALL COST ANALYSIS{reset}")
    hr("═")
    print(f"  Show:    {bold}{report.show_name}{reset}")
    print(f"  Venue:   {report.venue}")
    print(f"  Date:    {report.install_date}")
    print(f"  Moves/yr: {report.moves_per_year}")
    hr()

    # Summary
    print(f"\n{bold}  FINANCIAL SUMMARY{reset}")
    print(f"  Total Install Cost:        {bold}{_fmt(report.total_cost)}{reset}")
    print(f"  Optimal Cost (benchmark):  {green}{_fmt(report.total_optimal)}{reset}")
    print(f"  {red}Identified Waste:           {_fmt(report.total_waste)} ({report.waste_pct:.1f}%){reset}")
    print(f"  {gold}Projected Annual Savings:   {bold}{_fmt(report.annual_savings)}{reset}")
    hr()

    # Category breakdown
    print(f"\n{bold}  CATEGORY BREAKDOWN{reset}\n")
    print(f"  {'Category':<26} {'Spend':>10} {'Waste':>10} {'Waste %':>8}")
    print(f"  {'─' * 26} {'─' * 10} {'─' * 10} {'─' * 8}")
    for c in sorted(report.categories, key=lambda x: x.waste, reverse=True):
        color = red if c.waste_pct > 15 else (gold if c.waste_pct > 8 else green)
        print(f"  {c.label:<26} {_fmt(c.total_spend):>10} {color}{_fmt(c.waste):>10} {c.waste_pct:>6.1f}%{reset}")
    hr()

    # Top 5 waste items
    print(f"\n{bold}  TOP 5 WASTE AREAS{reset}\n")
    for i, item in enumerate(report.top_waste_items, 1):
        print(f"  {red}{i}. {item.description}{reset}")
        print(f"     Waste: {_fmt(item.waste)} | {item.notes or f'{item.waste_pct:.0f}% over benchmark'}")
        print()
    hr()

    # Waste drivers by category
    print(f"\n{bold}  WASTE DRIVERS BY CATEGORY{reset}\n")
    for c in sorted(report.categories, key=lambda x: x.waste, reverse=True):
        if not c.waste_drivers:
            continue
        print(f"  {gold}{c.label}{reset} — {_fmt(c.waste)} waste")
        for d in c.waste_drivers[:3]:
            print(f"    {dim}>{reset} {d}")
        print()
    hr()

    # Recommendations
    print(f"\n{bold}  RECOMMENDATIONS{reset}\n")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {green}{i}.{reset} {rec}")
        print()
    hr()

    # AI Analysis
    if report.ai_analysis:
        print(f"\n{bold}  AI-POWERED ANALYSIS{reset}\n")
        for line in report.ai_analysis.split("\n"):
            print(f"  {line}")
        print()
        hr()

    print(f"\n{dim}  Report generated by AUROS AI — {datetime.now().strftime('%Y-%m-%d %H:%M')}{reset}")
    hr("═")
    print()


# ═══════════════════════════════════════════════════════════════════════════════
#  OUTPUT: JSON
# ═══════════════════════════════════════════════════════════════════════════════

def export_json(report: InstallReport, path: str | Path | None = None) -> str:
    """Export report as JSON. Returns JSON string; optionally writes to file."""
    data = json.dumps(report.to_dict(), indent=2, default=str)
    if path:
        Path(path).write_text(data, encoding="utf-8")
        print(f"  JSON report saved to: {path}")
    return data


# ═══════════════════════════════════════════════════════════════════════════════
#  OUTPUT: HTML
# ═══════════════════════════════════════════════════════════════════════════════

def export_html(report: InstallReport, path: str | Path | None = None) -> str:
    """Generate a professional HTML report with AUROS dark theme."""
    d = report.to_dict()
    s = d["summary"]

    # Build category rows
    cat_rows = ""
    for c in sorted(d["categories"], key=lambda x: x["waste"], reverse=True):
        waste_class = "high" if c["waste_pct"] > 15 else ("med" if c["waste_pct"] > 8 else "low")
        cat_rows += f"""
            <tr>
                <td>{c['label']}</td>
                <td class="num">{_fmt(c['total_spend'])}</td>
                <td class="num">{_fmt(c['optimal_spend'])}</td>
                <td class="num waste-{waste_class}">{_fmt(c['waste'])}</td>
                <td class="num waste-{waste_class}">{c['waste_pct']:.1f}%</td>
            </tr>"""

    # Build top waste items
    top_items_html = ""
    for i, item in enumerate(d["top_5_waste_areas"], 1):
        top_items_html += f"""
            <div class="waste-item">
                <div class="waste-rank">{i}</div>
                <div class="waste-detail">
                    <strong>{item['description']}</strong>
                    <span class="waste-amount">{_fmt(item['waste_amount'])}</span>
                    <p class="waste-note">{item.get('notes', '')}</p>
                </div>
            </div>"""

    # Build recommendations
    recs_html = ""
    for i, rec in enumerate(d["recommendations"], 1):
        recs_html += f"""
            <div class="rec">
                <div class="rec-num">{i}</div>
                <div class="rec-text">{rec}</div>
            </div>"""

    # Build waste drivers
    drivers_html = ""
    for c in sorted(d["categories"], key=lambda x: x["waste"], reverse=True):
        if not c["waste_drivers"]:
            continue
        driver_list = "".join(f"<li>{d}</li>" for d in c["waste_drivers"][:3])
        drivers_html += f"""
            <div class="driver-group">
                <h4>{c['label']} <span class="driver-total">{_fmt(c['waste'])} waste</span></h4>
                <ul>{driver_list}</ul>
            </div>"""

    # AI analysis section
    ai_section = ""
    if d.get("ai_analysis"):
        ai_text = d["ai_analysis"].replace("\n", "<br>")
        ai_section = f"""
        <section class="report-section">
            <h2>AI-Powered Analysis</h2>
            <div class="ai-analysis">{ai_text}</div>
        </section>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Install Cost Analysis — {report.show_name} | AUROS AI</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        background: #08080c;
        color: #f0ece4;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        padding: 40px 20px;
    }}
    .container {{ max-width: 1100px; margin: 0 auto; }}

    /* Header */
    .report-header {{
        border-bottom: 2px solid #c9a84c;
        padding-bottom: 30px;
        margin-bottom: 40px;
    }}
    .brand {{ color: #c9a84c; font-size: 14px; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 8px; }}
    h1 {{ font-size: 32px; font-weight: 700; margin-bottom: 4px; }}
    .meta {{ color: #8a8780; font-size: 15px; }}
    .meta span {{ margin-right: 24px; }}

    /* Summary Cards */
    .summary-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 20px;
        margin-bottom: 50px;
    }}
    .card {{
        background: #111118;
        border: 1px solid #222230;
        border-radius: 12px;
        padding: 24px;
    }}
    .card-label {{ color: #8a8780; font-size: 13px; text-transform: uppercase; letter-spacing: 1px; }}
    .card-value {{ font-size: 28px; font-weight: 700; margin-top: 6px; }}
    .card-sub {{ font-size: 13px; color: #8a8780; margin-top: 2px; }}
    .card-value.gold {{ color: #c9a84c; }}
    .card-value.red {{ color: #e85454; }}
    .card-value.green {{ color: #4caf50; }}

    /* Sections */
    .report-section {{
        margin-bottom: 50px;
    }}
    .report-section h2 {{
        font-size: 20px;
        color: #c9a84c;
        border-bottom: 1px solid #222230;
        padding-bottom: 10px;
        margin-bottom: 20px;
    }}

    /* Tables */
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}
    th {{
        text-align: left;
        padding: 12px 16px;
        background: #111118;
        color: #c9a84c;
        font-weight: 600;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}
    th.num, td.num {{ text-align: right; }}
    td {{
        padding: 12px 16px;
        border-bottom: 1px solid #1a1a24;
    }}
    tr:hover td {{ background: #0d0d14; }}
    .waste-high {{ color: #e85454; font-weight: 600; }}
    .waste-med {{ color: #c9a84c; }}
    .waste-low {{ color: #4caf50; }}

    /* Top Waste Items */
    .waste-item {{
        display: flex;
        align-items: flex-start;
        gap: 16px;
        padding: 16px 0;
        border-bottom: 1px solid #1a1a24;
    }}
    .waste-rank {{
        background: #e85454;
        color: #fff;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 14px;
        flex-shrink: 0;
    }}
    .waste-detail {{ flex: 1; }}
    .waste-detail strong {{ font-size: 15px; }}
    .waste-amount {{ float: right; color: #e85454; font-weight: 700; font-size: 16px; }}
    .waste-note {{ color: #8a8780; font-size: 13px; margin-top: 4px; }}

    /* Recommendations */
    .rec {{
        display: flex;
        gap: 16px;
        padding: 18px 20px;
        background: #111118;
        border: 1px solid #222230;
        border-radius: 10px;
        margin-bottom: 12px;
        border-left: 3px solid #c9a84c;
    }}
    .rec-num {{
        color: #c9a84c;
        font-weight: 700;
        font-size: 18px;
        flex-shrink: 0;
        width: 24px;
    }}
    .rec-text {{ font-size: 14px; line-height: 1.7; }}

    /* Waste Drivers */
    .driver-group {{
        margin-bottom: 20px;
    }}
    .driver-group h4 {{
        font-size: 15px;
        margin-bottom: 8px;
    }}
    .driver-total {{
        color: #e85454;
        font-weight: 400;
        font-size: 13px;
        margin-left: 8px;
    }}
    .driver-group ul {{
        list-style: none;
        padding-left: 0;
    }}
    .driver-group li {{
        padding: 6px 0 6px 20px;
        border-left: 2px solid #222230;
        font-size: 13px;
        color: #aaa8a0;
        margin-bottom: 4px;
    }}

    /* AI Analysis */
    .ai-analysis {{
        background: #111118;
        border: 1px solid #c9a84c33;
        border-radius: 10px;
        padding: 24px;
        font-size: 14px;
        line-height: 1.8;
    }}

    /* Footer */
    .report-footer {{
        border-top: 1px solid #222230;
        padding-top: 20px;
        color: #555;
        font-size: 12px;
        text-align: center;
    }}
    .report-footer .brand-mark {{ color: #c9a84c; }}

    @media print {{
        body {{ background: #fff; color: #111; padding: 20px; }}
        .card {{ border: 1px solid #ddd; background: #f9f9f9; }}
        .waste-high {{ color: #c0392b; }}
        .waste-med {{ color: #e67e22; }}
        .card-value.gold, .brand, h2, .rec-num {{ color: #b8941f; }}
    }}
</style>
</head>
<body>
<div class="container">

    <header class="report-header">
        <div class="brand">AUROS AI &mdash; Install Cost Analysis</div>
        <h1>{report.show_name}</h1>
        <div class="meta">
            <span>{report.venue}</span>
            <span>Install: {report.install_date}</span>
            <span>{report.moves_per_year} moves/year</span>
        </div>
    </header>

    <div class="summary-grid">
        <div class="card">
            <div class="card-label">Total Install Cost</div>
            <div class="card-value">{_fmt(s['total_install_cost'])}</div>
        </div>
        <div class="card">
            <div class="card-label">Optimal Benchmark</div>
            <div class="card-value green">{_fmt(s['optimal_cost'])}</div>
        </div>
        <div class="card">
            <div class="card-label">Identified Waste</div>
            <div class="card-value red">{_fmt(s['total_identified_waste'])}</div>
            <div class="card-sub">{s['waste_percentage']:.1f}% of total spend</div>
        </div>
        <div class="card">
            <div class="card-label">Projected Annual Savings</div>
            <div class="card-value gold">{_fmt(s['projected_annual_savings'])}</div>
            <div class="card-sub">across {report.moves_per_year} moves/year</div>
        </div>
    </div>

    <section class="report-section">
        <h2>Cost Breakdown by Category</h2>
        <table>
            <thead>
                <tr>
                    <th>Category</th>
                    <th class="num">Actual Spend</th>
                    <th class="num">Optimal</th>
                    <th class="num">Waste</th>
                    <th class="num">Waste %</th>
                </tr>
            </thead>
            <tbody>{cat_rows}
            </tbody>
        </table>
    </section>

    <section class="report-section">
        <h2>Top 5 Waste Areas</h2>
        {top_items_html}
    </section>

    <section class="report-section">
        <h2>Waste Drivers</h2>
        {drivers_html}
    </section>

    <section class="report-section">
        <h2>Recommendations</h2>
        {recs_html}
    </section>

    {ai_section}

    <footer class="report-footer">
        <span class="brand-mark">AUROS AI</span> &mdash; Install Cost Analysis Report &mdash; Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}
    </footer>

</div>
</body>
</html>"""

    if path:
        Path(path).write_text(html, encoding="utf-8")
        print(f"  HTML report saved to: {path}")
    return html


# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API — for programmatic use
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_install(
    data_path: str | Path | None = None,
    demo: bool = False,
    use_ai: bool = False,
    output_path: str | Path | None = None,
    output_format: str = "terminal",
    moves_per_year: int | None = None,
) -> InstallReport:
    """
    Main entry point for programmatic use.

    Args:
        data_path: Path to CSV or Excel file with install data
        demo: If True, use built-in demo data
        use_ai: If True, use Claude API for AI-powered analysis
        output_path: Optional file path to write report
        output_format: 'terminal', 'json', or 'html'
        moves_per_year: Override moves/year for annual projection

    Returns:
        InstallReport object with full analysis
    """
    if demo:
        meta, items = generate_demo_data()
    elif data_path:
        meta, items = load_data(data_path)
    else:
        raise ValueError("Provide --data <path> or --demo")

    if moves_per_year is not None:
        meta["moves_per_year"] = moves_per_year

    report = analyze(meta, items, use_ai=use_ai)

    # Determine output format from path extension if not specified
    if output_path:
        ext = Path(output_path).suffix.lower()
        if ext == ".html":
            output_format = "html"
        elif ext == ".json":
            output_format = "json"

    # Output
    if output_format == "html":
        export_html(report, output_path)
    elif output_format == "json":
        result = export_json(report, output_path)
        if not output_path:
            print(result)
    else:
        print_terminal_report(report)
        if output_path:
            # Also save as JSON alongside terminal output
            export_json(report, output_path)

    return report


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="AUROS AI — Install Cost Analyzer for Live Entertainment Productions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/install_analyzer.py --demo
  python tools/install_analyzer.py --demo --output report.html
  python tools/install_analyzer.py --demo --output report.json
  python tools/install_analyzer.py --data install_data.csv
  python tools/install_analyzer.py --data install_data.csv --ai --output analysis.html
  python tools/install_analyzer.py --data costs.xlsx --moves 4
        """,
    )
    parser.add_argument("--demo", action="store_true", help="Run with realistic demo data")
    parser.add_argument("--data", type=str, help="Path to CSV or Excel file with install data")
    parser.add_argument("--output", "-o", type=str, help="Output file path (.html, .json)")
    parser.add_argument("--format", choices=["terminal", "json", "html"], default="terminal",
                        help="Output format (default: terminal)")
    parser.add_argument("--ai", action="store_true", help="Include AI-powered analysis via Claude")
    parser.add_argument("--moves", type=int, help="Override moves per year for annual projection")

    args = parser.parse_args()

    if not args.demo and not args.data:
        parser.print_help()
        print("\nError: Specify --demo or --data <path>")
        sys.exit(1)

    fmt = args.format
    if args.output and fmt == "terminal":
        ext = Path(args.output).suffix.lower()
        if ext == ".html":
            fmt = "html"
        elif ext == ".json":
            fmt = "json"

    analyze_install(
        data_path=args.data,
        demo=args.demo,
        use_ai=args.ai,
        output_path=args.output,
        output_format=fmt,
        moves_per_year=args.moves,
    )


if __name__ == "__main__":
    main()
