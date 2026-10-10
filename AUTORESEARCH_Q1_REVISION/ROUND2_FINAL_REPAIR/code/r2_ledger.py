"""Append-only decision ledger for ROUND2 with REAL UTC timestamps.

Usage:
  python r2_ledger.py append "<decision>" "<rationale>" "<evidence paths>"
  python r2_ledger.py show
"""
import datetime
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
LEDGER = os.path.join(R2, "results", "decisions_round2.log")
HEADER = (
    "# decisions_round2.log (append-only; real UTC system-clock timestamps)\n"
    "# format: ISO8601-UTC | decision | rationale | evidence/paths\n"
)


def ensure():
    if not os.path.exists(LEDGER):
        with io.open(LEDGER, "w", encoding="utf-8", newline="\n") as f:
            f.write(HEADER)


def append(decision, rationale, evidence):
    ensure()
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat(
        timespec="seconds")
    for field in (decision, rationale, evidence):
        if "\t" in field or "\n" in field:
            raise SystemExit("ledger fields must be single-line, tab-free")
    with io.open(LEDGER, "a", encoding="utf-8", newline="\n") as f:
        f.write(f"{ts} | {decision} | {rationale} | {evidence}\n")
    print(f"appended @ {ts}")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "show":
        ensure()
        sys.stdout.write(io.open(LEDGER, encoding="utf-8").read())
        return
    if len(sys.argv) != 5 or sys.argv[1] != "append":
        raise SystemExit(__doc__)
    append(sys.argv[2], sys.argv[3], sys.argv[4])


if __name__ == "__main__":
    main()
