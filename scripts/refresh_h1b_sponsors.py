#!/usr/bin/env python3
"""
Rebuild config/h1b_sponsors.json from the public USCIS H-1B Employer Data Hub.

The sponsor list is a curated starter set; run this yearly to refresh it from
authoritative data. It does NOT hit the network — download the CSV yourself:

    https://www.uscis.gov/tools/reports-and-studies/h-1b-employer-data-hub
    (Data Hub Files → download the fiscal-year CSV)

Then:

    python scripts/refresh_h1b_sponsors.py --csv ~/Downloads/h1b_datahubexport-2025.csv
    python scripts/refresh_h1b_sponsors.py --csv <file> --min-approvals 250 --dry-run

Employers with total approvals >= --min-approvals are kept. Existing curated
entries in the current JSON are preserved (union), so hand-added AI labs / target
companies that fall below the threshold aren't dropped.
"""

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
SPONSORS_PATH = ROOT / "config" / "h1b_sponsors.json"


def _find_col(header: list[str], *needles: str) -> int | None:
    for i, col in enumerate(header):
        low = col.lower()
        if all(n in low for n in needles):
            return i
    return None


def _parse_int(val: str) -> int:
    try:
        return int(str(val).replace(",", "").strip() or 0)
    except ValueError:
        return 0


def load_from_csv(csv_path: Path, min_approvals: int) -> dict[str, int]:
    """Aggregate total approvals per employer from the USCIS CSV."""
    with csv_path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        header = next(reader)
        name_col = _find_col(header, "employer") or _find_col(header, "petitioner")
        if name_col is None:
            sys.exit(f"Could not find an employer/petitioner column in {header}")
        approval_cols = [
            i for i, c in enumerate(header) if "approval" in c.lower()
        ]
        if not approval_cols:
            sys.exit(f"Could not find any approval columns in {header}")

        totals: dict[str, int] = {}
        for row in reader:
            if len(row) <= name_col:
                continue
            name = (row[name_col] or "").strip()
            if not name:
                continue
            approvals = sum(_parse_int(row[i]) for i in approval_cols if i < len(row))
            totals[name] = totals.get(name, 0) + approvals

    return {n: t for n, t in totals.items() if t >= min_approvals}


def _title_case(name: str) -> str:
    """USCIS names are ALL CAPS; make them presentable (load-time normalization
    handles matching regardless)."""
    return " ".join(w.capitalize() if w.isupper() else w for w in name.split())


def main() -> None:
    ap = argparse.ArgumentParser(description="Rebuild config/h1b_sponsors.json from the USCIS CSV.")
    ap.add_argument("--csv", type=Path, required=True, help="Path to the USCIS H-1B Employer Data Hub CSV")
    ap.add_argument("--min-approvals", type=int, default=200, help="Keep employers with >= this many approvals")
    ap.add_argument("--dry-run", action="store_true", help="Print a summary without writing")
    args = ap.parse_args()

    if not args.csv.exists():
        sys.exit(f"CSV not found: {args.csv}")

    from_csv = load_from_csv(args.csv, args.min_approvals)
    print(f"{len(from_csv)} employers with >= {args.min_approvals} approvals in {args.csv.name}")

    # Preserve the current curated entries (union).
    existing: list = []
    try:
        cur = json.loads(SPONSORS_PATH.read_text(encoding="utf-8"))
        existing = cur.get("sponsors", []) if isinstance(cur, dict) else cur
    except (OSError, ValueError):
        pass
    existing_names = [e.get("name") if isinstance(e, dict) else e for e in existing]

    merged = {n: None for n in existing_names if n}          # preserve order-ish, dedupe
    for name in sorted(from_csv, key=lambda n: -from_csv[n]):
        merged.setdefault(_title_case(name), None)

    sponsors = list(merged.keys())
    print(f"{len(existing_names)} curated + CSV → {len(sponsors)} total sponsors")

    if args.dry_run:
        print("Dry run — not writing. Top 15 CSV employers:")
        for name in sorted(from_csv, key=lambda n: -from_csv[n])[:15]:
            print(f"  {from_csv[name]:>7,}  {_title_case(name)}")
        return

    payload = {
        "source": "USCIS H-1B Employer Data Hub (refresh_h1b_sponsors.py) + curated JobApply targets.",
        "generated": date.today().isoformat(),
        "note": (
            "Names normalized at load (lowercase, suffixes stripped, token-subset match). "
            "Soft scoring boost by default; require_sponsor filter is opt-in. "
            f"Rebuilt from CSV with min_approvals={args.min_approvals}."
        ),
        "sponsors": sponsors,
    }
    SPONSORS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(sponsors)} sponsors → {SPONSORS_PATH}")


if __name__ == "__main__":
    main()
