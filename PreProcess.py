import json
import csv

INPUT_FILE = "event_vessel_depart_40_hm.json"
OUTPUT_FILE = "vessel_event_40.csv"


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for record in data:
        row = {k: v for k, v in record.items() if k != "qcDetails"}
        qc = record.get("qcDetails", {})
        row["num_of_qc"] = len(qc) if qc else 0
        rows.append(row)

    fieldnames = list(rows[0].keys()) if rows else []

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Done – {len(rows)} rows written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
