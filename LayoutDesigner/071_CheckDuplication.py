"""
071_CheckDuplication.py
Check for duplicate points (same x, y coordinates) across all layout and routing JSON files.
Scans data/path/*.json and data/routing/*_point.json pairs.
"""
import json
import sys
import os
import glob
from collections import defaultdict

# Fix Windows stdout encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = "data"
PATH_DIR = os.path.join(BASE_DIR, "path")
ROUTING_DIR = os.path.join(BASE_DIR, "routing")
OUTPUT_DIR = os.path.join(ROUTING_DIR, "duplication")


def load_layout_points(filepath):
    """Load points from layout JSON file (dict of categories -> list of points)"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for category, items in data.items():
        for item in items:
            points.append({
                "id": item.get("id"),
                "x": item.get("x"),
                "y": item.get("y"),
                "source": "layout",
                "category": category
            })
    return points


def load_routing_points(filepath):
    """Load points from routing JSON file (has 'points' array)"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for item in data.get("points", []):
        points.append({
            "id": item.get("id"),
            "x": item.get("x"),
            "y": item.get("y"),
            "source": "routing",
            "category": item.get("region", "unknown")
        })
    return points


def find_duplicates(all_points):
    """Group points by (x, y) and find duplicates"""
    coord_map = defaultdict(list)
    for p in all_points:
        key = (p["x"], p["y"])
        coord_map[key].append(p)

    return {k: v for k, v in coord_map.items() if len(v) > 1}


def process_pair(layout_file, routing_file, output_file):
    """Process a single layout/routing pair and write results"""
    layout_points = load_layout_points(layout_file)
    routing_points = load_routing_points(routing_file)

    all_points = layout_points + routing_points
    duplicates = find_duplicates(all_points)

    layout_name = os.path.basename(layout_file)
    routing_name = os.path.basename(routing_file)

    if not duplicates:
        print(f"  [OK] {layout_name} + {routing_name}: No duplicates found")
        return 0

    print(f"  [DUP] {layout_name} + {routing_name}: {len(duplicates)} duplicate groups")

    # Build output data
    dup_data = {
        "layout_file": layout_name,
        "routing_file": routing_name,
        "layout_points_count": len(layout_points),
        "routing_points_count": len(routing_points),
        "duplicate_groups": {}
    }

    for idx, (coord, points) in enumerate(duplicates.items(), 1):
        x, y = coord
        key = f"dup_{idx:03d}"
        dup_data["duplicate_groups"][key] = {
            "x": x,
            "y": y,
            "count": len(points),
            "points": [
                {"id": p["id"], "source": p["source"], "category": p["category"]}
                for p in points
            ]
        }

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dup_data, f, indent=2, ensure_ascii=False)

    return len(duplicates)


def main():
    print("=" * 60)
    print("Check Point Duplication Across All Layout Files")
    print("=" * 60)

    # Find all routing point files
    routing_pattern = os.path.join(ROUTING_DIR, "*_point.json")
    routing_files = glob.glob(routing_pattern)

    if not routing_files:
        print("No routing point files found.")
        return

    print(f"\nFound {len(routing_files)} routing file(s)\n")

    total_dup_groups = 0

    for routing_file in sorted(routing_files):
        # Derive layout filename by removing "_point" suffix
        routing_basename = os.path.basename(routing_file)
        layout_basename = routing_basename.replace("_point.json", ".json")
        layout_file = os.path.join(PATH_DIR, layout_basename)

        if not os.path.exists(layout_file):
            print(f"  [SKIP] {routing_basename}: corresponding layout file not found ({layout_basename})")
            continue

        # Output file: data/routing/duplication/{layout_name_without_ext}_dup.json
        dup_basename = layout_basename.replace(".json", "_dup.json")
        output_file = os.path.join(OUTPUT_DIR, dup_basename)

        count = process_pair(layout_file, routing_file, output_file)
        total_dup_groups += count

    print(f"\n{'=' * 60}")
    print(f"Total: {total_dup_groups} duplicate groups across {len(routing_files)} file pair(s)")
    print(f"Results written to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
