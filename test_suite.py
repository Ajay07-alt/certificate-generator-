"""
Comprehensive automated test suite for Visual Bulk Certificate Generator.
Tests data models, Excel loader, dynamic 1-page/2-page certificate generator,
and GUI initialization without default templates.
"""

import sys
import os
from pathlib import Path
import pymupdf

# Ensure utf-8 stdout
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from models import PlaceholderItem, ProjectConfig
from generator import CertificateGenerator, ExcelDataLoader, sanitize_filename

def test_models():
    print("[1/5] Testing Data Models & Page Count...")
    item = PlaceholderItem(name="Student Name", x=100, y=200, width=500, height=80, font_size=55)
    d = item.to_dict()
    item2 = PlaceholderItem.from_dict(d)
    assert item2.name == "Student Name"
    assert item2.x == 100
    assert item2.font_size == 55

    cfg = ProjectConfig(page_count=1, naming_pattern="{Register No}_{Name}.pdf", items=[item])
    cfg_d = cfg.to_dict()
    assert cfg_d["page_count"] == 1
    assert len(cfg_d["items"]) == 1

    cfg2 = ProjectConfig.load_from_json("assets/default_layout.json")
    assert cfg2.page_count in [1, 2]
    print("  ✓ Models passed.")

def test_excel_loader():
    print("[2/5] Testing Excel Loader...")
    # Test cleaned sample data
    df1, cols1, meta1 = ExcelDataLoader.load("assets/sample_data.xlsx")
    assert len(df1) == 5, f"Expected 5 rows, got {len(df1)}"
    assert "Name" in cols1
    assert "Register No" in cols1

    # Test raw robotics lab data
    raw_path = "assets/robotics_lab_data.xlsx"
    if Path(raw_path).exists():
        df2, cols2, meta2 = ExcelDataLoader.load(raw_path, sheet_name="AIML")
        assert len(df2) == 30, f"Expected 30 rows in AIML, got {len(df2)}"
        assert "Student Attendance" in df2.columns
        assert "Certificate No" in df2.columns
        print(f"  ✓ Raw Excel parsed accurately: {len(df2)} students, Department: {meta2.get('Department')}")
    print("  ✓ Excel Loader passed.")

def test_single_page_generation():
    print("[3/5] Testing Single-Page (Count = 1) Generation Engine...")
    out_dir = Path("test_single_page_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load 1-page config
    cfg = ProjectConfig(
        page_count=1,
        front_template_path=str(Path("assets/front_template.png").resolve()),
        excel_data_path=str(Path("assets/sample_data.xlsx").resolve()),
        signature_path=str(Path("assets/sample_signature.png").resolve()),
        output_dir=str(out_dir.resolve()),
        items=[
            PlaceholderItem(name="Name", page_index=0, x=1130, y=1210, width=1530, height=85, font_size=58),
            PlaceholderItem(name="Register No", page_index=0, x=1215, y=1320, width=420, height=75, font_size=50),
        ]
    )

    gen = CertificateGenerator(cfg)
    generated = gen.generate_all()
    assert len(generated) == 5, f"Expected 5 PDFs, got {len(generated)}"

    for pdf in generated:
        assert pdf.exists()
        doc = pymupdf.open(str(pdf))
        # MUST BE EXACTLY 1 PAGE
        assert len(doc) == 1, f"Expected exactly 1 page in single-page mode, got {len(doc)} in {pdf.name}"
        w = round(doc[0].rect.width, 1)
        h = round(doc[0].rect.height, 1)
        assert (w, h) == (842.4, 595.7), f"Unexpected page size: ({w}, {h})"
        doc.close()

    print(f"  ✓ Successfully verified {len(generated)} SINGLE-PAGE (count=1) PDFs in {out_dir.name}.")

def test_two_page_generation():
    print("[4/5] Testing Two-Page (Count = 2) Generation Engine...")
    out_dir = Path("test_two_page_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = ProjectConfig.load_from_json("assets/default_layout.json")
    cfg.page_count = 2
    cfg.output_dir = str(out_dir.resolve())
    cfg.excel_data_path = str(Path("assets/sample_data.xlsx").resolve())

    gen = CertificateGenerator(cfg)
    generated = gen.generate_all()
    assert len(generated) == 5, f"Expected 5 PDFs, got {len(generated)}"

    for pdf in generated:
        assert pdf.exists()
        doc = pymupdf.open(str(pdf))
        # MUST BE EXACTLY 2 PAGES
        assert len(doc) == 2, f"Expected exactly 2 pages in 2-page mode, got {len(doc)} in {pdf.name}"
        doc.close()

    print(f"  ✓ Successfully verified {len(generated)} TWO-PAGE (count=2) PDFs in {out_dir.name}.")

def test_gui_page_count_and_clean_defaults():
    print("[5/5] Testing Desktop GUI Clean Defaults & Page Count Switcher...")
    from ui_main import MainWindow
    app = MainWindow()
    app.update()

    # 1. Verify default templates are NOT loaded automatically on startup
    assert app.config.front_template_path == "", "Default Front template should NOT be loaded on startup"
    assert app.config.back_template_path == "", "Default Back template should NOT be loaded on startup"
    assert app.front_status_lbl.cget("text") == "Not Loaded"
    assert app.page_count == 1, "App should start in 1-page mode by default"
    assert len(app.notebook.tabs()) == 1, "Notebook should have only 1 tab in 1-page mode"
    print("  ✓ Verified default templates are removed; starts clean with 1-page mode.")

    # 2. Test switching to 2 Pages (Front & Back)
    app.set_page_count(2)
    assert app.page_count == 2
    assert len(app.notebook.tabs()) == 2, "Notebook should have 2 tabs in 2-page mode"
    assert str(app.back_btn.cget("state")) == "normal", "Back upload button should be enabled"
    print("  ✓ Switch to 2 Pages verified (Front & Back tabs active).")

    # 3. Test switching back to 1 Page (Front Only)
    app.set_page_count(1)
    assert app.page_count == 1
    assert len(app.notebook.tabs()) == 1, "Notebook should have 1 tab in 1-page mode"
    assert str(app.back_btn.cget("state")) == "disabled", "Back upload button should be disabled in 1-page mode"
    print("  ✓ Switch back to 1 Page verified (only Front Page active).")

    # 4. Test Excel Sheet/Page Changer
    sheets = app.sheet_combo["values"]
    assert len(sheets) >= 5, f"Expected multiple sheets in workbook, got {sheets}"
    app.sheet_combo.set("CSE")
    app._on_sheet_selection_changed()
    assert len(app.canvas_front.all_rows) == 30, f"Expected 30 students in CSE, got {len(app.canvas_front.all_rows)}"
    print(f"  ✓ Sheet changer verified: switched to 'CSE' with {len(app.canvas_front.all_rows)} students.")

    # 5. Test Student Navigator (Prev/Next)
    assert app.canvas_front.current_row_idx == 0
    app.canvas_front._next_student()
    assert app.canvas_front.current_row_idx == 1
    app.canvas_front._prev_student()
    assert app.canvas_front.current_row_idx == 0
    print("  ✓ Student navigator (Prev/Next) verified.")

    app.destroy()
    print("  ✓ GUI clean lifecycle verified with 100% success.")

if __name__ == "__main__":
    print("==================================================")
    print("  RUNNING VISUAL BULK CERTIFICATE GENERATOR TESTS  ")
    print("==================================================")
    test_models()
    test_excel_loader()
    test_single_page_generation()
    test_two_page_generation()
    test_gui_page_count_and_clean_defaults()
    print("==================================================")
    print("  ALL 5 TEST SUITES PASSED WITH 100% SUCCESS!    ")
    print("==================================================")
