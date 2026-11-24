"""Run the 14 data-quality tests for P28 and write outputs/test_results.json.

Each test file returns its violating rows. All 14 expect 0 rows.
Exit code 0 when all 14 pass.

Usage:  python3 src/run_tests.py
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "pipeline.db"
TESTS_DIR = ROOT / "sql" / "tests"
OUT = ROOT / "outputs" / "test_results.json"


def main():
    conn = sqlite3.connect(DB)
    results = []
    for path in sorted(TESTS_DIR.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        rows = conn.execute(sql).fetchall()
        passed = len(rows) == 0
        results.append({"test": path.name, "status": "PASS" if passed else "FAIL",
                        "violations": len(rows), "expected": 0})
        print(f"{'PASS' if passed else 'FAIL'}  {path.name}  "
              f"(violations: {len(rows)}, expected: 0)")
    passed = sum(1 for r in results if r["status"] == "PASS")
    payload = {"total": len(results), "passed": passed, "tests": results}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"{passed}/{len(results)} tests passing -> {OUT}")
    conn.close()
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
