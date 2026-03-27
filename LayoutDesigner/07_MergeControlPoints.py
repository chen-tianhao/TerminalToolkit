"""
07_MergeControlPoints.py
Merge layout (path) files with routing (point) files.
- Copy all lists from data/path/ file as-is
- Add a new "junction" list containing non-duplicate points from data/routing/
- Points with matching x,y are considered duplicates
"""
import json
import sys
import os
import glob

# Fix Windows stdout encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE_DIR = "data"
PATH_DIR = os.path.join(BASE_DIR, "path")
ROUTING_DIR = os.path.join(BASE_DIR, "routing")
OUTPUT_DIR = os.path.join(ROUTING_DIR, "merged")


def load_path_points(filepath):
    """Load all points from path layout file (dict of categories -> list of points)"""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    points = []
    for category, items in data.items():
        for item in items:
            points.append({
                "x": item.get("x"),
                "y": item.get("y")
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
            "region": item.get("region"),
            "meta": item.get("meta"),
            "inout": item.get("inout"),
            "next": item.get("next")
        })
    return points


def is_duplicate(point, path_points_set):
    """Check if a point (x, y) already exists in path points set"""
    return (point["x"], point["y"]) in path_points_set


def merge_files(layout_file, routing_file, output_file):
    """Merge layout and routing files, output to merged folder/"""
    # Load path points (to check for duplicates)
    path_points = load_path_points(layout_file)
    path_points_set = set((p["x"], p["y"]) for p in path_points)

    # Load routing points
    routing_points = load_routing_points(routing_file)

    # Load full layout data
    with open(layout_file, "r", encoding="utf-8") as f:
        layout_data = json.load(f)

    # Filter non-duplicate routing points for "junction" list
    junction_points = []
    for p in routing_points:
        if not is_duplicate(p, path_points_set):
            junction_points.append({
                "id": p["id"],
                "x": p["x"],
                "y": p["y"],
                "region": p["region"],
                "meta": p["meta"],
                "inout": p["inout"],
                "next": p["next"]
            })

    # Add junction list to layout data
    layout_data["junction"] = junction_points

    # Write output
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(layout_data, f, indent=2, ensure_ascii=False)

    layout_name = os.path.basename(layout_file)
    routing_name = os.path.basename(routing_file)
    print(f"  [OK] {layout_name} + {routing_name}")
    print(f"       Path points: {len(path_points)}, Junction points: {len(junction_points)}")
    print(f"       -> {os.path.basename(output_file)}")


def main():
    print("=" * 60)
    print("Merge Control Points: Path + Routing")
    print("=" * 60)

    # Find all routing point files
    routing_pattern = os.path.join(ROUTING_DIR, "*_point.json")
    routing_files = glob.glob(routing_pattern)

    if not routing_files:
        print("No routing point files found.")
        return

    print(f"\nFound {len(routing_files)} routing file(s)\n")

    for routing_file in sorted(routing_files):
        # Derive layout filename by removing "_point" suffix
        routing_basename = os.path.basename(routing_file)
        layout_basename = routing_basename.replace("_point.json", ".json")
        layout_file = os.path.join(PATH_DIR, layout_basename)

        if not os.path.exists(layout_file):
            print(f"  [SKIP] {routing_basename}: corresponding layout file not found ({layout_basename})")
            continue

        # Output file: data/merged/{layout_name_without_ext}_merged.json
        output_basename = layout_basename.replace(".json", "_merged.json")
        output_file = os.path.join(OUTPUT_DIR, output_basename)

        merge_files(layout_file, routing_file, output_file)

    print(f"\n{'=' * 60}")
    print(f"Output written to: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()