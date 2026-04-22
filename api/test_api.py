"""
Local smoke tests for the JobApply FastAPI backend.

Usage (with the API server already running on port 8000):
    python api/test_api.py

Or start the server and run tests in one shot:
    uvicorn api.main:app --port 8000 & sleep 2 && python api/test_api.py

Exit code 0 = all tests passed.
"""

import sys
import json
import time
import requests

BASE = "http://localhost:8000/api"
PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append(ok)
    status = PASS if ok else FAIL
    print(f"  {status}  {name}" + (f"  →  {detail}" if detail else ""))
    return ok


def req(method, path, **kwargs):
    try:
        r = requests.request(method, BASE + path, timeout=10, **kwargs)
        return r
    except requests.ConnectionError:
        print(f"\n\033[31mERROR: Cannot connect to {BASE}\033[0m")
        print("Make sure the API server is running:  uvicorn api.main:app --port 8000\n")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
print("\n── Stats ────────────────────────────────────────────────")
r = req("GET", "/stats")
check("GET /stats → 200", r.status_code == 200)
s = r.json()
check("stats has required keys", all(k in s for k in ["total","new","applied","offer"]), str(list(s.keys())))

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Focus ────────────────────────────────────────────────")
r = req("GET", "/focus")
check("GET /focus → 200", r.status_code == 200)
check("focus returns list", isinstance(r.json(), list))

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Jobs list ────────────────────────────────────────────")
r = req("GET", "/jobs")
check("GET /jobs → 200", r.status_code == 200)
body = r.json()
check("jobs response has 'jobs' key", "jobs" in body)
check("jobs response has 'total' key", "total" in body)

r2 = req("GET", "/jobs", params={"status": "new", "limit": 5})
check("GET /jobs?status=new&limit=5 → 200", r2.status_code == 200)

r3 = req("GET", "/jobs", params={"min_score": 0.7, "sort": "company"})
check("GET /jobs?min_score=0.7&sort=company → 200", r3.status_code == 200)

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Import ───────────────────────────────────────────────")
payload = {
    "title":        "_Test Job (auto-test, safe to delete)",
    "company":      "_TestCo",
    "url":          "",
    "status":       "new",
    "date_applied": None,
    "location":     "Remote",
    "notes":        "Created by api/test_api.py",
}
r = req("POST", "/jobs/import", json=payload)
check("POST /jobs/import → 200/201", r.status_code in (200, 201))
import_body = r.json()
check("import returns job id", "id" in import_body, str(import_body))
test_id = import_body.get("id")

# Second import of same URL → should update, not 500
r_dup = req("POST", "/jobs/import", json=payload)
check("duplicate import → 200 (update)", r_dup.status_code == 200)
check("duplicate returns 'updated' status", r_dup.json().get("status") in ("updated", "created"))

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Single job ───────────────────────────────────────────")
if test_id:
    r = req("GET", f"/jobs/{test_id}")
    check(f"GET /jobs/{test_id} → 200", r.status_code == 200)
    job = r.json()
    check("job has title field",   "title"   in job)
    check("job has company field", "company" in job)
    check("job has status field",  "status"  in job)
    check("title matches",  job.get("title")   == payload["title"],   job.get("title"))
    check("company matches",job.get("company") == payload["company"], job.get("company"))

r_404 = req("GET", "/jobs/999999999")
check("GET /jobs/999999999 → 404", r_404.status_code == 404)

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Patch ────────────────────────────────────────────────")
if test_id:
    r = req("PATCH", f"/jobs/{test_id}", json={"notes": "patched by test", "starred": 1})
    check(f"PATCH /jobs/{test_id} → 200", r.status_code == 200)
    patched = r.json()
    check("notes updated", patched.get("notes") == "patched by test", patched.get("notes"))
    check("starred updated", patched.get("starred") == 1, str(patched.get("starred")))

    r2 = req("PATCH", f"/jobs/{test_id}", json={"status": "skipped"})
    check("PATCH status → 200", r2.status_code == 200)
    check("status is now skipped", r2.json().get("status") == "skipped")

r_404p = req("PATCH", "/jobs/999999999", json={"notes": "x"})
check("PATCH /jobs/999999999 → 404", r_404p.status_code == 404)

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Resume / Cover letter (no-resume paths) ──────────────")
if test_id:
    r = req("GET", f"/jobs/{test_id}/resume")
    check(f"GET /jobs/{test_id}/resume → 404 (no resume yet)", r.status_code == 404)

    r = req("GET", f"/jobs/{test_id}/cover_letter")
    check(f"GET /jobs/{test_id}/cover_letter → 404 (no CL yet)", r.status_code == 404)

# ─────────────────────────────────────────────────────────────────────────────
print("\n── Summary ──────────────────────────────────────────────")
passed = sum(results)
total  = len(results)
color  = "\033[32m" if passed == total else "\033[31m"
print(f"\n  {color}{passed}/{total} checks passed\033[0m\n")
sys.exit(0 if passed == total else 1)
