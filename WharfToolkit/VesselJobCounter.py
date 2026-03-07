import json

INPUT_FILE = "event_vessel_depart_40_hm.json"


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = []
    for record in data:
        if record.get("eventName") == "OnStart":
            total = record.get("discharging", 0) + record.get("loading", 0)
            results.append((record["vesselId"], total))

    results.sort(key=lambda x: x[1], reverse=True)

    print(f"{'vesselId':<12} {'sum':>8}")
    print("-" * 21)
    for vid, total in results:
        print(f"{vid:<12} {total:>8}")


if __name__ == "__main__":
    main()
