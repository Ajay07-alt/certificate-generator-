"""
Comprehensive automated tests for FastAPI Web Server endpoints.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from pathlib import Path
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)

def run_tests():
    print("\n==================================================")
    print("  RUNNING WEB SERVER & API ENDPOINT TESTS")
    print("==================================================")

    # 1. Test Root HTML
    print("[1/6] Testing Root '/' Endpoint...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "Visual Bulk Certificate Generator" in res.text
    print("  ✓ Root SPA page served successfully.")

    # 2. Test Initial State
    print("[2/6] Testing Initial '/api/state'...")
    res = client.get("/api/state")
    assert res.status_code == 200
    state = res.json()
    assert state["page_count"] == 1
    print("  ✓ State initialized cleanly.")

    # 3. Test Excel Upload & Sheet Switching
    print("[3/6] Testing '/api/upload/excel' and '/api/excel/sheet'...")
    excel_file = Path("assets/robotics_lab_data.xlsx")
    assert excel_file.exists(), "assets/robotics_lab_data.xlsx missing"
    with open(excel_file, "rb") as f:
        res = client.post("/api/upload/excel", files={"file": ("robotics_lab_data.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["sheets"]) == 11, f"Expected 11 sheets, got {len(data['sheets'])}"
    assert data["total_students"] == 30
    print(f"  ✓ Excel loaded: {len(data['sheets'])} sheets, {data['total_students']} students.")

    # Switch sheet to CSE
    res = client.post("/api/excel/sheet", json={"sheet_name": "CSE"})
    assert res.status_code == 200
    sheet_data = res.json()
    assert sheet_data["active_sheet"] == "CSE"
    assert sheet_data["total_students"] == 30
    print("  ✓ Switched to 'CSE' sheet successfully.")

    # 4. Test Template Upload
    print("[4/6] Testing '/api/upload/template'...")
    front_img = Path("assets/front_template.png")
    assert front_img.exists()
    with open(front_img, "rb") as f:
        res = client.post("/api/upload/template", data={"page_index": 0}, files={"file": ("front_template.png", f, "image/png")})
    assert res.status_code == 200, res.text
    tpl_data = res.json()
    assert tpl_data["dimensions"]["width"] > 0
    print(f"  ✓ Template uploaded: dimensions {tpl_data['dimensions']['width']}x{tpl_data['dimensions']['height']}.")

    # 5. Test Auto-Place
    print("[5/6] Testing '/api/auto-place'...")
    res = client.get("/api/auto-place")
    assert res.status_code == 200
    auto_data = res.json()
    assert len(auto_data["items"]) >= 4
    items = auto_data["items"]
    print(f"  ✓ Auto-place created {len(items)} placeholder items.")

    # 6. Test Live Preview and Bulk Generation
    print("[6/6] Testing '/api/preview' and '/api/generate'...")
    preview_payload = {
        "page_index": 0,
        "student_index": 0,
        "page_count": 1,
        "selected_sheet": "CSE",
        "items": items
    }
    res = client.post("/api/preview", json=preview_payload)
    assert res.status_code == 200, res.text
    prev_data = res.json()
    assert prev_data["status"] == "success"
    assert prev_data["preview_b64"].startswith("data:image/jpeg;base64,")
    print(f"  ✓ Live preview rendered for student: {prev_data['student_info']['name']}")

    # Test Bulk Generation for single-page mode
    gen_payload = {
        "page_count": 1,
        "selected_sheet": "CSE",
        "generate_all_sheets": False,
        "naming_pattern": "{Register No}_{Name}.pdf",
        "items": items
    }
    res = client.post("/api/generate", json=gen_payload)
    assert res.status_code == 200, res.text
    gen_data = res.json()
    assert gen_data["total_generated"] == 30
    assert gen_data["download_zip_url"] == "/api/download/certificates_bundle.zip"
    print(f"  ✓ Bulk generation passed: {gen_data['total_generated']} certificates generated and zipped.")

    # Test Download ZIP
    res = client.get("/api/download/certificates_bundle.zip")
    assert res.status_code == 200
    assert len(res.content) > 1000
    print(f"  ✓ Download ZIP endpoint verified ({len(res.content)} bytes).")

    print("==================================================")
    print("  ALL 6 WEB ENDPOINT TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================\n")

if __name__ == "__main__":
    run_tests()
