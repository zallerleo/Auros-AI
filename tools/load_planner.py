#!/usr/bin/env python3
"""
AUROS AI — Truck Load Planner

Optimizes truck load planning for live entertainment production companies
that pack 20-40+ trucks per move. Uses first-fit-decreasing bin packing
to show the gap between current (gut-feel) truck counts and optimal packing.

Usage:
    python tools/load_planner.py --demo
    python tools/load_planner.py --inventory items.csv --truck-type 53ft --cost-per-truck 2500
    python tools/load_planner.py --inventory items.csv --truck-type custom --custom-volume 3000 --custom-weight 40000
"""

import argparse
import csv
import json
import math
import os
import random
import sys
from copy import deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional, Dict, Tuple

# ──────────────────────────────────────────────────────────────────────
# Truck Specifications
# ──────────────────────────────────────────────────────────────────────

TRUCK_SPECS = {
    "53ft": {
        "name": "53' Semi Trailer",
        "length_ft": 53,
        "width_ft": 8.5,
        "height_ft": 9.0,
        "volume_cuft": 3489,
        "max_weight_lbs": 45000,
    },
    "48ft": {
        "name": "48' Semi Trailer",
        "length_ft": 48,
        "width_ft": 8.5,
        "height_ft": 9.0,
        "volume_cuft": 3174,
        "max_weight_lbs": 44000,
    },
    "26ft": {
        "name": "26' Box Truck",
        "length_ft": 26,
        "width_ft": 8.0,
        "height_ft": 8.5,
        "volume_cuft": 1800,
        "max_weight_lbs": 10000,
    },
    "sprinter": {
        "name": "Sprinter Van",
        "length_ft": 12,
        "width_ft": 5.8,
        "height_ft": 7.0,
        "volume_cuft": 488,
        "max_weight_lbs": 3500,
    },
}


# ──────────────────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────────────────

@dataclass
class InventoryItem:
    name: str
    item_id: str
    length_ft: float
    width_ft: float
    height_ft: float
    weight_lbs: float
    quantity: int = 1
    category: str = "general"
    fragile: bool = False
    load_first: bool = False
    load_last: bool = False
    group: str = ""

    @property
    def volume_cuft(self) -> float:
        return self.length_ft * self.width_ft * self.height_ft

    @property
    def total_volume(self) -> float:
        return self.volume_cuft * self.quantity

    @property
    def total_weight(self) -> float:
        return self.weight_lbs * self.quantity


@dataclass
class TruckAssignment:
    truck_id: int
    truck_type: str
    truck_name: str
    max_volume: float
    max_weight: float
    items: List[dict] = field(default_factory=list)
    used_volume: float = 0.0
    used_weight: float = 0.0

    @property
    def volume_util_pct(self) -> float:
        return (self.used_volume / self.max_volume * 100) if self.max_volume else 0

    @property
    def weight_util_pct(self) -> float:
        return (self.used_weight / self.max_weight * 100) if self.max_weight else 0


# ──────────────────────────────────────────────────────────────────────
# Inventory Loading
# ──────────────────────────────────────────────────────────────────────

def load_inventory_csv(path: str) -> List[InventoryItem]:
    """Load inventory from CSV file.

    Expected columns: name, item_id, length, width, height, weight, quantity,
    category, fragile, load_first, load_last, group, unit (ft or in)
    """
    items = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            unit = row.get("unit", "ft").strip().lower()
            divisor = 12.0 if unit == "in" else 1.0
            items.append(InventoryItem(
                name=row["name"].strip(),
                item_id=row.get("item_id", "").strip() or f"ITEM-{len(items)+1:04d}",
                length_ft=float(row["length"]) / divisor,
                width_ft=float(row["width"]) / divisor,
                height_ft=float(row["height"]) / divisor,
                weight_lbs=float(row["weight"]),
                quantity=int(row.get("quantity", 1)),
                category=row.get("category", "general").strip(),
                fragile=row.get("fragile", "").strip().lower() in ("true", "1", "yes"),
                load_first=row.get("load_first", "").strip().lower() in ("true", "1", "yes"),
                load_last=row.get("load_last", "").strip().lower() in ("true", "1", "yes"),
                group=row.get("group", "").strip(),
            ))
    return items


# ──────────────────────────────────────────────────────────────────────
# Bin Packing (First-Fit Decreasing by Volume)
# ──────────────────────────────────────────────────────────────────────

def expand_items(items: List[InventoryItem]) -> List[InventoryItem]:
    """Expand quantity > 1 into individual unit entries for packing."""
    expanded = []
    for item in items:
        for i in range(item.quantity):
            clone = InventoryItem(
                name=item.name,
                item_id=f"{item.item_id}#{i+1}" if item.quantity > 1 else item.item_id,
                length_ft=item.length_ft,
                width_ft=item.width_ft,
                height_ft=item.height_ft,
                weight_lbs=item.weight_lbs,
                quantity=1,
                category=item.category,
                fragile=item.fragile,
                load_first=item.load_first,
                load_last=item.load_last,
                group=item.group,
            )
            expanded.append(clone)
    return expanded


def first_fit_decreasing(items: List[InventoryItem], truck_spec: dict) -> List[TruckAssignment]:
    """First-Fit Decreasing bin packing with group and fragile constraints."""
    expanded = expand_items(items)

    # Separate grouped items
    groups: Dict[str, List[InventoryItem]] = {}
    ungrouped: List[InventoryItem] = []
    for it in expanded:
        if it.group:
            groups.setdefault(it.group, []).append(it)
        else:
            ungrouped.append(it)

    # Sort ungrouped by volume descending (FFD)
    ungrouped.sort(key=lambda x: x.volume_cuft, reverse=True)

    max_vol = truck_spec["volume_cuft"]
    max_wt = truck_spec["max_weight_lbs"]
    truck_type_key = truck_spec.get("key", "custom")
    truck_name = truck_spec["name"]

    trucks: List[TruckAssignment] = []

    def new_truck() -> TruckAssignment:
        t = TruckAssignment(
            truck_id=len(trucks) + 1,
            truck_type=truck_type_key,
            truck_name=truck_name,
            max_volume=max_vol,
            max_weight=max_wt,
        )
        trucks.append(t)
        return t

    def try_place(item: InventoryItem, truck: TruckAssignment) -> bool:
        vol = item.volume_cuft
        wt = item.weight_lbs
        if truck.used_volume + vol <= truck.max_volume and truck.used_weight + wt <= truck.max_weight:
            # Fragile items ride on top — we just note it; real 3D packing is out of scope
            truck.items.append({
                "name": item.name,
                "item_id": item.item_id,
                "volume_cuft": round(vol, 2),
                "weight_lbs": round(wt, 1),
                "category": item.category,
                "fragile": item.fragile,
                "load_first": item.load_first,
                "load_last": item.load_last,
                "group": item.group,
            })
            truck.used_volume += vol
            truck.used_weight += wt
            return True
        return False

    # 1. Place grouped items first — keep each group on one truck if possible
    for gname, gitems in sorted(groups.items()):
        grp_vol = sum(i.volume_cuft for i in gitems)
        grp_wt = sum(i.weight_lbs for i in gitems)
        placed = False
        for truck in trucks:
            if truck.used_volume + grp_vol <= truck.max_volume and truck.used_weight + grp_wt <= truck.max_weight:
                for it in gitems:
                    try_place(it, truck)
                placed = True
                break
        if not placed:
            # Need new truck(s). If group exceeds single truck, split across minimum trucks.
            remaining = list(gitems)
            remaining.sort(key=lambda x: x.volume_cuft, reverse=True)
            while remaining:
                t = new_truck()
                still_remaining = []
                for it in remaining:
                    if not try_place(it, t):
                        still_remaining.append(it)
                remaining = still_remaining

    # 2. Place ungrouped items via FFD
    for item in ungrouped:
        placed = False
        for truck in trucks:
            if try_place(item, truck):
                placed = True
                break
        if not placed:
            t = new_truck()
            try_place(item, t)

    # 3. Sort items within each truck: load_first items first, load_last items last, fragile last
    for truck in trucks:
        def sort_key(it):
            if it["load_first"]:
                return 0
            if it["fragile"]:
                return 3
            if it["load_last"]:
                return 4
            return 1
        truck.items.sort(key=sort_key)
        truck.used_volume = round(truck.used_volume, 2)
        truck.used_weight = round(truck.used_weight, 1)

    return trucks


# ──────────────────────────────────────────────────────────────────────
# Analysis / Calculations
# ──────────────────────────────────────────────────────────────────────

def analyze(items: List[InventoryItem], truck_spec: dict, current_truck_count: int,
            cost_per_truck: float) -> dict:
    """Run full analysis: totals, minimums, packing, savings."""
    total_vol = sum(it.total_volume for it in items)
    total_wt = sum(it.total_weight for it in items)
    total_units = sum(it.quantity for it in items)

    max_vol = truck_spec["volume_cuft"]
    max_wt = truck_spec["max_weight_lbs"]

    min_by_volume = math.ceil(total_vol / max_vol)
    min_by_weight = math.ceil(total_wt / max_wt)
    theoretical_min = max(min_by_volume, min_by_weight)

    trucks = first_fit_decreasing(items, truck_spec)
    optimal_count = len(trucks)

    avg_util = sum(t.volume_util_pct for t in trucks) / len(trucks) if trucks else 0
    avg_weight_util = sum(t.weight_util_pct for t in trucks) / len(trucks) if trucks else 0

    current_avg_util = (total_vol / (current_truck_count * max_vol) * 100) if current_truck_count else 0

    trucks_eliminated = max(0, current_truck_count - optimal_count)
    savings_per_move = trucks_eliminated * cost_per_truck

    # Category breakdown
    cat_volumes: Dict[str, float] = {}
    cat_weights: Dict[str, float] = {}
    cat_counts: Dict[str, int] = {}
    for it in items:
        cat_volumes[it.category] = cat_volumes.get(it.category, 0) + it.total_volume
        cat_weights[it.category] = cat_weights.get(it.category, 0) + it.total_weight
        cat_counts[it.category] = cat_counts.get(it.category, 0) + it.quantity

    result = {
        "summary": {
            "total_items": total_units,
            "unique_items": len(items),
            "total_volume_cuft": round(total_vol, 1),
            "total_weight_lbs": round(total_wt, 1),
            "truck_type": truck_spec["name"],
            "truck_volume_cuft": max_vol,
            "truck_max_weight_lbs": max_wt,
        },
        "analysis": {
            "min_trucks_by_volume": min_by_volume,
            "min_trucks_by_weight": min_by_weight,
            "theoretical_minimum_trucks": theoretical_min,
            "optimal_trucks_packed": optimal_count,
            "current_truck_count": current_truck_count,
            "trucks_eliminated": trucks_eliminated,
            "current_avg_utilization_pct": round(current_avg_util, 1),
            "optimal_avg_volume_utilization_pct": round(avg_util, 1),
            "optimal_avg_weight_utilization_pct": round(avg_weight_util, 1),
        },
        "financials": {
            "cost_per_truck": cost_per_truck,
            "savings_per_move": savings_per_move,
            "savings_10_moves_per_year": savings_per_move * 10,
            "savings_20_moves_per_year": savings_per_move * 20,
        },
        "category_breakdown": {
            cat: {
                "count": cat_counts[cat],
                "volume_cuft": round(cat_volumes[cat], 1),
                "weight_lbs": round(cat_weights[cat], 1),
            }
            for cat in sorted(cat_volumes.keys())
        },
        "trucks": [
            {
                "truck_id": t.truck_id,
                "truck_name": f"{t.truck_name} #{t.truck_id}",
                "items_count": len(t.items),
                "used_volume_cuft": t.used_volume,
                "used_weight_lbs": t.used_weight,
                "volume_utilization_pct": round(t.volume_util_pct, 1),
                "weight_utilization_pct": round(t.weight_util_pct, 1),
                "items": t.items,
            }
            for t in trucks
        ],
    }
    return result


# ──────────────────────────────────────────────────────────────────────
# Demo Data Generator
# ──────────────────────────────────────────────────────────────────────

def generate_demo_inventory() -> Tuple[List[InventoryItem], int, float]:
    """Generate realistic inventory for a large touring exhibition.

    Returns (items, current_truck_count, cost_per_truck).
    Target: ~200 line items totalling ~120,000 cu ft across ~600+ units,
    currently using 40 trucks, optimal packing ~35-36 trucks.
    """
    random.seed(42)  # reproducible demo
    items: List[InventoryItem] = []
    idx = 0

    def add(name, l, w, h, wt, qty, cat, **kw):
        nonlocal idx
        idx += 1
        items.append(InventoryItem(
            name=name, item_id=f"EXH-{idx:04d}",
            length_ft=l, width_ft=w, height_ft=h,
            weight_lbs=wt, quantity=qty, category=cat, **kw,
        ))

    # ── CRATES & SCENIC (the bulk of any large show) ──────────────
    # Stage deck: 8x4x2 = 64 cu ft each x 260 = 16,640 cu ft
    add("Main Stage Deck Section", 8, 4, 2, 800, 260, "crates", group="stage-deck")
    # Risers: 6x4x1.5 = 36 cu ft each x 160 = 5,760 cu ft
    add("Stage Riser Module", 6, 4, 1.5, 450, 160, "crates", group="stage-deck")
    # Large scenic panels: 10x5x2 = 100 cu ft each x 80 = 8,000 cu ft
    add("Scenic Backdrop Panel A", 10, 5, 2, 650, 80, "set_pieces", group="backdrop-a")
    # Medium scenic panels: 8x5x2 = 80 cu ft each x 60 = 4,800 cu ft
    add("Scenic Backdrop Panel B", 8, 5, 2, 500, 60, "set_pieces", group="backdrop-b")
    # Scenic arch frames: 12x4x3 = 144 cu ft each x 30 = 4,320 cu ft
    add("Scenic Arch Frame", 12, 4, 3, 950, 30, "set_pieces")
    # Scenic flats: 8x4x1 = 32 cu ft each x 180 = 5,760 cu ft
    add("Scenic Flat - Painted", 8, 4, 1, 200, 180, "set_pieces")
    # Large prop crates: 6x4x4 = 96 cu ft each x 60 = 5,760 cu ft
    add("Prop Crate - Large", 6, 4, 4, 700, 60, "crates")
    # Medium prop crates: 4x4x3 = 48 cu ft each x 90 = 4,320 cu ft
    add("Prop Crate - Medium", 4, 4, 3, 400, 90, "crates")
    # Scenic column wraps: 3x3x8 = 72 cu ft each x 40 = 2,880 cu ft
    add("Decorative Column Wrap", 3, 3, 8, 350, 40, "set_pieces")
    # Overhead scenic canopy: 10x8x1 = 80 cu ft each x 24 = 1,920 cu ft
    add("Scenic Canopy Frame", 10, 8, 1, 400, 24, "set_pieces")
    # Scenic wing flats: 6x4x2 = 48 cu ft each x 36 = 1,728 cu ft
    add("Wing Flat - Scenic", 6, 4, 2, 300, 36, "set_pieces")
    # Custom scenic elements: 5x3x3 = 45 cu ft each x 20 = 900 cu ft
    add("Custom Scenic Element Crate", 5, 3, 3, 350, 20, "crates")

    # ── AV EQUIPMENT ──────────────────────────────────────────────
    # LED video wall: 6x4x4 = 96 cu ft each x 48 = 4,608 cu ft
    add("LED Video Wall Crate", 6, 4, 4, 1200, 48, "av_equipment", fragile=True, group="video-wall")
    # Video wall processors: 2x2x6 = 24 cu ft each x 10 = 240 cu ft
    add("Video Wall Processor Rack", 2, 2, 6, 350, 10, "av_equipment", fragile=True, group="video-wall")
    # Audio racks: 2x2.5x6 = 30 cu ft each x 24 = 720 cu ft
    add("Main Audio Rack", 2, 2.5, 6, 500, 24, "av_equipment", fragile=True)
    # Monitor speakers: 3x2x2.5 = 15 cu ft each x 64 = 960 cu ft
    add("Monitor Speaker Cabinet", 3, 2, 2.5, 250, 64, "av_equipment")
    # Line array: 4x2x1.5 = 12 cu ft each x 80 = 960 cu ft
    add("Line Array Module", 4, 2, 1.5, 180, 80, "av_equipment", group="line-array")
    # Line array frames: 4x4x6 = 96 cu ft each x 16 = 1,536 cu ft
    add("Line Array Frame", 4, 4, 6, 600, 16, "av_equipment", group="line-array")
    # Subwoofers: 3x2.5x2.5 = 18.75 cu ft each x 48 = 900 cu ft
    add("Subwoofer Cabinet", 3, 2.5, 2.5, 300, 48, "av_equipment")
    # Projection crates: 4x3x3 = 36 cu ft each x 16 = 576 cu ft
    add("Projector Crate - 30K Lumen", 4, 3, 3, 450, 16, "av_equipment", fragile=True)

    # ── LIGHTING ──────────────────────────────────────────────────
    # Moving heads: 3x2x2 = 12 cu ft each x 120 = 1,440 cu ft
    add("Moving Head Light Case", 3, 2, 2, 150, 120, "lighting", fragile=True)
    # 10ft truss: 10x1.5x1.5 = 22.5 cu ft each x 160 = 3,600 cu ft
    add("Truss Section 10ft", 10, 1.5, 1.5, 130, 160, "lighting", group="truss")
    # 5ft truss: 5x1.5x1.5 = 11.25 cu ft each x 80 = 900 cu ft
    add("Truss Section 5ft", 5, 1.5, 1.5, 70, 80, "lighting", group="truss")
    # Lighting consoles: 4x2.5x3 = 30 cu ft each x 6 = 180 cu ft
    add("Lighting Control Console", 4, 2.5, 3, 280, 6, "lighting", fragile=True, load_last=True)
    # Par cans: 3x2x2 = 12 cu ft each x 48 = 576 cu ft
    add("Par Can Road Case (6-pack)", 3, 2, 2, 180, 48, "lighting")
    # Dimmer racks: 2x2x6 = 24 cu ft each x 24 = 576 cu ft
    add("Dimmer Rack", 2, 2, 6, 400, 24, "lighting")
    # Follow spots: 5x2x3 = 30 cu ft each x 16 = 480 cu ft
    add("Follow Spot", 5, 2, 3, 200, 16, "lighting", fragile=True)
    # Haze machines: 2x2x2 = 8 cu ft each x 12 = 96 cu ft
    add("Haze Machine Case", 2, 2, 2, 120, 12, "lighting")

    # ── DISPLAY / EXHIBITION ─────────────────────────────────────
    # Large display cases: 6x4x7 = 168 cu ft each x 32 = 5,376 cu ft
    add("Glass Display Case - Large", 6, 4, 7, 900, 32, "display", fragile=True, group="display-lg")
    # Medium display cases: 4x3x6 = 72 cu ft each x 48 = 3,456 cu ft
    add("Glass Display Case - Medium", 4, 3, 6, 550, 48, "display", fragile=True, group="display-md")
    # Small display cases: 3x2x5 = 30 cu ft each x 40 = 1,200 cu ft
    add("Glass Display Case - Small", 3, 2, 5, 300, 40, "display", fragile=True, group="display-sm")
    # Artifact crates: 3x2x2 = 12 cu ft each x 60 = 720 cu ft
    add("Artifact Crate - Padded", 3, 2, 2, 200, 60, "display", fragile=True)
    # Pedestals: 2x2x3 = 12 cu ft each x 48 = 576 cu ft
    add("Pedestal Base", 2, 2, 3, 150, 48, "display")
    # Stanchions: 4x2x2 = 16 cu ft each x 20 = 320 cu ft
    add("Stanchion & Rope Set (10)", 4, 2, 2, 100, 20, "display")
    # Wall panels: 8x0.5x4 = 16 cu ft each x 160 = 2,560 cu ft
    add("Wall Panel - Fabric Wrapped", 8, 0.5, 4, 120, 160, "set_pieces")

    # ── FURNITURE ─────────────────────────────────────────────────
    # VIP sofas: 7x3x3 = 63 cu ft each x 16 = 1,008 cu ft
    add("VIP Lounge Sofa", 7, 3, 3, 250, 16, "furniture")
    # Tables: 3x3x1 = 9 cu ft each x 40 = 360 cu ft
    add("High-Top Table (folded)", 3, 3, 1, 80, 40, "furniture")
    # Chair carts: 5x3x5 = 75 cu ft each x 16 = 1,200 cu ft
    add("Folding Chair Cart (40 chairs)", 5, 3, 5, 700, 16, "furniture")
    # Reg desk: 6x2.5x3.5 = 52.5 cu ft each x 12 = 630 cu ft
    add("Registration Desk Section", 6, 2.5, 3.5, 350, 12, "furniture", group="reg-desk")
    # Branded counters: 4x2x3.5 = 28 cu ft each x 8 = 224 cu ft
    add("Branded Counter", 4, 2, 3.5, 200, 8, "furniture", group="reg-desk")
    # Lounge chairs: 3x3x3 = 27 cu ft each x 24 = 648 cu ft
    add("Lounge Chair - Upholstered", 3, 3, 3, 120, 24, "furniture")

    # ── CONSUMABLES & TOOLS ───────────────────────────────────────
    # Cable trunks: 4x2x2 = 16 cu ft each x 32 = 512 cu ft
    add("Cable Trunk (power)", 4, 2, 2, 250, 32, "consumables")
    add("Cable Trunk (data/signal)", 4, 2, 2, 200, 32, "consumables")
    add("Cable Trunk (AV/HDMI)", 4, 2, 2, 180, 16, "consumables")
    # Supplies: 2x1.5x1.5 = 4.5 cu ft each
    add("Gaffer Tape & Supplies Box", 2, 1.5, 1.5, 60, 24, "consumables")
    add("Hardware Box (bolts, clamps)", 2, 1.5, 1.5, 80, 20, "tools")
    add("Tool Case - Electrician", 3, 1.5, 1.5, 70, 12, "tools", load_last=True)
    add("Tool Case - Carpenter", 3, 1.5, 1.5, 90, 12, "tools", load_last=True)
    add("Tool Case - Rigging", 3, 2, 2, 120, 12, "tools", load_last=True)
    add("Safety Equipment Bin", 3, 2, 2, 100, 16, "tools", load_last=True)
    add("First Aid / Emergency Kit", 2, 1.5, 1.5, 40, 8, "tools", load_last=True)
    add("Cleaning Supplies Cart", 3, 2, 4, 150, 8, "consumables")

    # ── POWER / INFRASTRUCTURE ────────────────────────────────────
    # Generators: 8x4x5 = 160 cu ft each x 12 = 1,920 cu ft
    add("Generator (towable)", 8, 4, 5, 3000, 12, "infrastructure", load_first=True)
    # Power distro: 3x2x2.5 = 15 cu ft each x 36 = 540 cu ft
    add("Power Distribution Box", 3, 2, 2.5, 300, 36, "infrastructure")
    # HVAC: 5x3x4 = 60 cu ft each x 12 = 720 cu ft
    add("HVAC Portable Unit", 5, 3, 4, 500, 12, "infrastructure", load_first=True)
    # Cable ramp: 4x2x0.5 = 4 cu ft each x 60 = 240 cu ft
    add("Cable Ramp Section", 4, 2, 0.5, 60, 60, "infrastructure")

    # ── SIGNAGE ───────────────────────────────────────────────────
    add("Large Banner Tube", 8, 0.5, 0.5, 30, 40, "signage")
    add("Freestanding Sign Frame", 4, 2, 7, 150, 24, "signage")
    add("Directional Sign Box", 3, 2, 2, 40, 20, "signage")
    add("Hanging Banner Crate", 6, 3, 2, 120, 16, "signage")

    # ── FLOORING ──────────────────────────────────────────────────
    # Flooring crates: 8x4x2 = 64 cu ft each x 140 = 8,960 cu ft
    add("Carpet Tile Crate", 8, 4, 2, 600, 140, "flooring")
    # Dance floor: 4x4x1 = 16 cu ft each x 100 = 1,600 cu ft
    add("Dance Floor Section", 4, 4, 1, 120, 100, "flooring", group="dance-floor")
    # Ramp sections: 6x4x1.5 = 36 cu ft each x 24 = 864 cu ft
    add("ADA Ramp Section", 6, 4, 1.5, 250, 24, "flooring")

    # ── DRAPE / SOFT GOODS ────────────────────────────────────────
    # Drape bins: 4x3x3 = 36 cu ft each x 48 = 1,728 cu ft
    add("Drape Bin - Black Velour", 4, 3, 3, 200, 48, "soft_goods")
    add("Drape Bin - Custom Print", 4, 3, 3, 180, 24, "soft_goods")
    # Pipe & drape: 8x1x1 = 8 cu ft each x 60 = 480 cu ft
    add("Pipe & Drape Kit", 8, 1, 1, 80, 60, "soft_goods")

    # ── RIGGING ───────────────────────────────────────────────────
    # Motor cases: 3x2x2 = 12 cu ft each x 60 = 720 cu ft
    add("Chain Motor Case", 3, 2, 2, 250, 60, "rigging")
    # Rigging hardware: 3x2x2 = 12 cu ft each x 24 = 288 cu ft
    add("Rigging Hardware Case", 3, 2, 2, 300, 24, "rigging")
    # Span sets / slings: 3x2x1 = 6 cu ft each x 20 = 120 cu ft
    add("Span Set & Sling Bag", 3, 2, 1, 100, 20, "rigging")

    current_truck_count = 40
    cost_per_truck = 2500.0

    return items, current_truck_count, cost_per_truck


# ──────────────────────────────────────────────────────────────────────
# HTML Report
# ──────────────────────────────────────────────────────────────────────

def generate_html_report(result: dict) -> str:
    s = result["summary"]
    a = result["analysis"]
    f = result["financials"]
    trucks = result["trucks"]
    cats = result["category_breakdown"]

    # Build truck rows
    truck_rows = ""
    for t in trucks:
        bar_color = "#00e676" if t["volume_utilization_pct"] >= 85 else (
            "#ffab00" if t["volume_utilization_pct"] >= 60 else "#ff5252")
        truck_rows += f"""
        <tr>
            <td>#{t['truck_id']}</td>
            <td>{t['items_count']}</td>
            <td>{t['used_volume_cuft']:,.1f}</td>
            <td>{t['used_weight_lbs']:,.0f}</td>
            <td>
                <div class="bar-bg"><div class="bar-fill" style="width:{t['volume_utilization_pct']}%;background:{bar_color}"></div></div>
                {t['volume_utilization_pct']}%
            </td>
            <td>{t['weight_utilization_pct']}%</td>
        </tr>"""

    # Category rows
    cat_rows = ""
    for cat, info in cats.items():
        cat_rows += f"""
        <tr>
            <td>{cat.replace('_', ' ').title()}</td>
            <td>{info['count']}</td>
            <td>{info['volume_cuft']:,.1f}</td>
            <td>{info['weight_lbs']:,.0f}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AUROS AI — Truck Load Plan</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #0a0a14;
        color: #e0e0e0;
        line-height: 1.6;
        padding: 40px 20px;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    h1 {{
        font-size: 2.2rem;
        color: #fff;
        margin-bottom: 8px;
    }}
    h1 span {{ color: #e94560; }}
    .subtitle {{ color: #888; margin-bottom: 40px; font-size: 0.95rem; }}
    h2 {{
        font-size: 1.3rem;
        color: #e94560;
        margin: 32px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e1e30;
    }}
    .cards {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 32px;
    }}
    .card {{
        background: #12121e;
        border: 1px solid #1e1e30;
        border-radius: 10px;
        padding: 20px;
    }}
    .card .label {{ font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
    .card .value {{ font-size: 1.8rem; font-weight: 700; color: #fff; margin-top: 4px; }}
    .card .value.green {{ color: #00e676; }}
    .card .value.red {{ color: #ff5252; }}
    .card .value.gold {{ color: #FFD700; }}
    .card .detail {{ font-size: 0.8rem; color: #666; margin-top: 4px; }}

    .savings-banner {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 2px solid #00e676;
        border-radius: 12px;
        padding: 28px;
        text-align: center;
        margin: 32px 0;
    }}
    .savings-banner .big {{ font-size: 2.4rem; font-weight: 800; color: #00e676; }}
    .savings-banner .sub {{ color: #aaa; margin-top: 8px; }}

    table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 24px;
    }}
    th {{
        text-align: left;
        padding: 10px 12px;
        background: #12121e;
        color: #888;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        border-bottom: 1px solid #1e1e30;
    }}
    td {{
        padding: 10px 12px;
        border-bottom: 1px solid #111;
        font-size: 0.9rem;
    }}
    tr:hover {{ background: #14142a; }}
    .bar-bg {{
        display: inline-block;
        width: 100px;
        height: 10px;
        background: #1e1e30;
        border-radius: 5px;
        overflow: hidden;
        vertical-align: middle;
        margin-right: 8px;
    }}
    .bar-fill {{
        height: 100%;
        border-radius: 5px;
    }}
    .footer {{
        text-align: center;
        color: #444;
        font-size: 0.75rem;
        margin-top: 60px;
        padding-top: 20px;
        border-top: 1px solid #111;
    }}
</style>
</head>
<body>
<div class="container">
    <h1><span>AUROS</span> AI — Truck Load Plan</h1>
    <p class="subtitle">Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')} &bull; {s['truck_type']}</p>

    <h2>Inventory Summary</h2>
    <div class="cards">
        <div class="card">
            <div class="label">Total Items</div>
            <div class="value">{s['total_items']:,}</div>
            <div class="detail">{s['unique_items']} unique line items</div>
        </div>
        <div class="card">
            <div class="label">Total Volume</div>
            <div class="value">{s['total_volume_cuft']:,.0f} <small>cu ft</small></div>
        </div>
        <div class="card">
            <div class="label">Total Weight</div>
            <div class="value">{s['total_weight_lbs']:,.0f} <small>lbs</small></div>
        </div>
        <div class="card">
            <div class="label">Truck Spec</div>
            <div class="value" style="font-size:1.2rem">{s['truck_type']}</div>
            <div class="detail">{s['truck_volume_cuft']:,} cu ft / {s['truck_max_weight_lbs']:,} lbs max</div>
        </div>
    </div>

    <h2>Optimization Analysis</h2>
    <div class="cards">
        <div class="card">
            <div class="label">Current Trucks</div>
            <div class="value red">{a['current_truck_count']}</div>
            <div class="detail">Avg utilization: {a['current_avg_utilization_pct']}%</div>
        </div>
        <div class="card">
            <div class="label">Optimal Trucks</div>
            <div class="value green">{a['optimal_trucks_packed']}</div>
            <div class="detail">Avg utilization: {a['optimal_avg_volume_utilization_pct']}%</div>
        </div>
        <div class="card">
            <div class="label">Theoretical Minimum</div>
            <div class="value">{a['theoretical_minimum_trucks']}</div>
            <div class="detail">Vol: {a['min_trucks_by_volume']} / Wt: {a['min_trucks_by_weight']}</div>
        </div>
        <div class="card">
            <div class="label">Trucks Eliminated</div>
            <div class="value gold">{a['trucks_eliminated']}</div>
            <div class="detail">{a['current_truck_count']} &rarr; {a['optimal_trucks_packed']}</div>
        </div>
    </div>

    <div class="savings-banner">
        <div class="big">${f['savings_per_move']:,.0f} saved per move</div>
        <div class="sub">
            {a['trucks_eliminated']} fewer trucks &times; ${f['cost_per_truck']:,.0f}/truck
            &bull; ${f['savings_10_moves_per_year']:,.0f}/yr (10 moves)
            &bull; ${f['savings_20_moves_per_year']:,.0f}/yr (20 moves)
        </div>
    </div>

    <h2>Category Breakdown</h2>
    <table>
        <thead><tr><th>Category</th><th>Items</th><th>Volume (cu ft)</th><th>Weight (lbs)</th></tr></thead>
        <tbody>{cat_rows}</tbody>
    </table>

    <h2>Truck Load Plan ({a['optimal_trucks_packed']} Trucks)</h2>
    <table>
        <thead><tr><th>Truck</th><th>Items</th><th>Volume</th><th>Weight</th><th>Vol. Utilization</th><th>Wt. Util.</th></tr></thead>
        <tbody>{truck_rows}</tbody>
    </table>

    <div class="footer">
        AUROS AI &mdash; Truck Load Planner &bull; First-Fit Decreasing Bin Packing &bull; Results are estimates; actual packing depends on item geometry and stacking.
    </div>
</div>
</body>
</html>"""
    return html


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AUROS AI — Truck Load Planner for live entertainment production",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/load_planner.py --demo
  python tools/load_planner.py --inventory items.csv --truck-type 53ft --cost-per-truck 2500
  python tools/load_planner.py --inventory items.csv --truck-type custom --custom-volume 3000 --custom-weight 40000
        """,
    )
    parser.add_argument("--demo", action="store_true", help="Run with built-in demo data (large touring exhibition)")
    parser.add_argument("--inventory", type=str, help="Path to inventory CSV file")
    parser.add_argument("--truck-type", type=str, default="53ft",
                        choices=list(TRUCK_SPECS.keys()) + ["custom"],
                        help="Truck type (default: 53ft)")
    parser.add_argument("--custom-volume", type=float, help="Custom truck volume in cu ft (requires --truck-type custom)")
    parser.add_argument("--custom-weight", type=float, help="Custom truck max weight in lbs (requires --truck-type custom)")
    parser.add_argument("--custom-name", type=str, default="Custom Truck", help="Name for custom truck type")
    parser.add_argument("--current-trucks", type=int, default=0,
                        help="Current number of trucks being used (for comparison)")
    parser.add_argument("--cost-per-truck", type=float, default=2500.0,
                        help="Cost per truck per move in USD (default: 2500)")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory (default: same as inventory or cwd)")
    parser.add_argument("--json-only", action="store_true", help="Output JSON only, no HTML report")

    args = parser.parse_args()

    if not args.demo and not args.inventory:
        parser.error("Provide --demo or --inventory <path>")

    # Resolve truck spec
    if args.truck_type == "custom":
        if not args.custom_volume or not args.custom_weight:
            parser.error("--truck-type custom requires --custom-volume and --custom-weight")
        truck_spec = {
            "key": "custom",
            "name": args.custom_name,
            "volume_cuft": args.custom_volume,
            "max_weight_lbs": args.custom_weight,
        }
    else:
        truck_spec = {**TRUCK_SPECS[args.truck_type], "key": args.truck_type}

    # Load data
    if args.demo:
        items, current_trucks, cost = generate_demo_inventory()
        if args.current_trucks > 0:
            current_trucks = args.current_trucks
        if args.cost_per_truck != 2500.0:
            cost = args.cost_per_truck
    else:
        items = load_inventory_csv(args.inventory)
        current_trucks = args.current_trucks if args.current_trucks > 0 else 0
        cost = args.cost_per_truck

    # Run analysis
    result = analyze(items, truck_spec, current_trucks, cost)

    # Determine output dir
    if args.output_dir:
        out_dir = args.output_dir
    elif args.inventory:
        out_dir = os.path.dirname(os.path.abspath(args.inventory))
    else:
        out_dir = os.path.dirname(os.path.abspath(__file__))

    os.makedirs(out_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Write JSON
    json_path = os.path.join(out_dir, f"load_plan_{timestamp}.json")
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[AUROS] JSON report: {json_path}")

    # Write HTML
    if not args.json_only:
        html_path = os.path.join(out_dir, f"load_plan_{timestamp}.html")
        with open(html_path, "w") as f:
            f.write(generate_html_report(result))
        print(f"[AUROS] HTML report: {html_path}")

    # Print summary to terminal
    a = result["analysis"]
    fin = result["financials"]
    print()
    print("=" * 60)
    print("  AUROS AI — TRUCK LOAD PLANNER RESULTS")
    print("=" * 60)
    print(f"  Total items:          {result['summary']['total_items']:,}")
    print(f"  Total volume:         {result['summary']['total_volume_cuft']:,.1f} cu ft")
    print(f"  Total weight:         {result['summary']['total_weight_lbs']:,.0f} lbs")
    print(f"  Truck type:           {result['summary']['truck_type']}")
    print("-" * 60)
    print(f"  Current trucks:       {a['current_truck_count']}")
    print(f"  Current avg util:     {a['current_avg_utilization_pct']}%")
    print(f"  Optimal trucks:       {a['optimal_trucks_packed']}")
    print(f"  Optimal avg util:     {a['optimal_avg_volume_utilization_pct']}% (vol) / {a['optimal_avg_weight_utilization_pct']}% (wt)")
    print(f"  Theoretical minimum:  {a['theoretical_minimum_trucks']}")
    print(f"  Trucks eliminated:    {a['trucks_eliminated']}")
    print("-" * 60)
    print(f"  Cost per truck:       ${fin['cost_per_truck']:,.0f}")
    print(f"  Savings per move:     ${fin['savings_per_move']:,.0f}")
    print(f"  Savings/yr (10 moves):${fin['savings_10_moves_per_year']:,.0f}")
    print(f"  Savings/yr (20 moves):${fin['savings_20_moves_per_year']:,.0f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
