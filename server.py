"""
Web Server for Visual Bulk Certificate Generator.
Powered by FastAPI, Uvicorn, Pillow, and PyMuPDF.
Supports local browser use and cloud/internet deployment.
"""

import os
import sys
import io
import json
import base64
import shutil
import zipfile
import webbrowser
from pathlib import Path
from typing import List, Dict, Any, Optional

import uvicorn
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from PIL import Image
import fitz  # PyMuPDF

from models import PlaceholderItem, ProjectConfig
from generator import CertificateGenerator, ExcelDataLoader, FontManager, sanitize_filename

# Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR = BASE_DIR / "output_certificates"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Visual Bulk Certificate Generator",
    description="Interactive Web Edition for generating bulk certificates from Excel data",
    version="2.0.0"
)

# Enable CORS for external/cloud access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global in-memory state
app_state = {
    "excel_path": "",
    "excel_sheets": [],
    "active_sheet": "",
    "current_df": None,
    "current_columns": [],
    "current_metadata": {},
    "front_template_path": "",
    "back_template_path": "",
    "signature_path": "",
    "page_count": 1,
    "placeholders": []
}

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


class PlaceholderPayload(BaseModel):
    id: str
    name: str = "Variable"
    page_index: int = 0
    x: float = 100.0
    y: float = 100.0
    width: float = 400.0
    height: float = 80.0
    font_family: str = "PTSerif-Bold"
    font_size: int = 50
    font_color: str = "#112354"
    alignment: str = "center"
    is_signature: bool = False
    image_path: Optional[str] = None
    auto_shrink: bool = True
    prefix: str = ""
    suffix: str = ""


class GenerateRequest(BaseModel):
    page_count: int = 1
    selected_sheet: str = ""
    generate_all_sheets: bool = False
    naming_pattern: str = "{Register No}_{Name}.pdf"
    items: List[PlaceholderPayload]


class PreviewRequest(BaseModel):
    page_index: int = 0
    student_index: int = 0
    page_count: int = 1
    selected_sheet: str = ""
    items: List[PlaceholderPayload]


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Visual Bulk Certificate Generator Web Interface Loading...</h1>", status_code=200)
    with open(index_file, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/state")
async def get_state():
    return {
        "excel_path": app_state["excel_path"],
        "excel_sheets": app_state["excel_sheets"],
        "active_sheet": app_state["active_sheet"],
        "columns": app_state["current_columns"],
        "metadata": app_state["current_metadata"],
        "student_count": len(app_state["current_df"]) if app_state["current_df"] is not None else 0,
        "front_template_path": app_state["front_template_path"],
        "back_template_path": app_state["back_template_path"],
        "signature_path": app_state["signature_path"],
        "page_count": app_state["page_count"]
    }


@app.post("/api/upload/template")
async def upload_template(file: UploadFile = File(...), page_index: int = Form(0)):
    """Uploads a template image (PNG/JPG) or multi-page PDF."""
    try:
        suffix = Path(file.filename).suffix.lower()
        save_path = UPLOADS_DIR / f"template_upload_{page_index}{suffix}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        detected_pages = 1
        page1_path = ""
        page2_path = ""
        dimensions = {"width": 2000, "height": 1414}

        if suffix == ".pdf":
            doc = fitz.open(str(save_path))
            detected_pages = len(doc)
            # Render page 1
            pix0 = doc[0].get_pixmap(dpi=300)
            page1_out = UPLOADS_DIR / "template_p1.png"
            pix0.save(str(page1_out))
            page1_path = str(page1_out)
            dimensions = {"width": pix0.width, "height": pix0.height}

            if detected_pages > 1:
                pix1 = doc[1].get_pixmap(dpi=300)
                page2_out = UPLOADS_DIR / "template_p2.png"
                pix1.save(str(page2_out))
                page2_path = str(page2_out)

            doc.close()
            if page_index == 0:
                app_state["front_template_path"] = page1_path
                if page2_path:
                    app_state["back_template_path"] = page2_path
                    app_state["page_count"] = 2
            else:
                app_state["back_template_path"] = page1_path
        else:
            with Image.open(save_path) as img:
                dimensions = {"width": img.width, "height": img.height}
            if page_index == 0:
                app_state["front_template_path"] = str(save_path)
            else:
                app_state["back_template_path"] = str(save_path)

        return {
            "status": "success",
            "page_index": page_index,
            "detected_pages": detected_pages,
            "dimensions": dimensions,
            "front_path": app_state["front_template_path"],
            "back_path": app_state["back_template_path"],
            "front_url": f"/uploads/{Path(app_state['front_template_path']).name}" if app_state['front_template_path'] else "",
            "back_url": f"/uploads/{Path(app_state['back_template_path']).name}" if app_state['back_template_path'] else "",
            "page_count": app_state["page_count"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload/excel")
async def upload_excel(file: UploadFile = File(...)):
    """Uploads Excel workbook, extracts department sheets and student data."""
    try:
        suffix = Path(file.filename).suffix.lower()
        save_path = UPLOADS_DIR / f"students_data{suffix}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        sheets = ExcelDataLoader.get_sheet_names(str(save_path))
        active_sheet = sheets[0] if sheets else "Default"
        df, columns, metadata = ExcelDataLoader.load(str(save_path), active_sheet)

        app_state["excel_path"] = str(save_path)
        app_state["excel_sheets"] = sheets
        app_state["active_sheet"] = active_sheet
        app_state["current_df"] = df
        app_state["current_columns"] = columns
        app_state["current_metadata"] = metadata

        # Prepare sample records
        sample_rows = df.head(5).fillna("").to_dict(orient="records")

        return {
            "status": "success",
            "sheets": sheets,
            "active_sheet": active_sheet,
            "columns": columns,
            "metadata": metadata,
            "total_students": len(df),
            "sample_rows": sample_rows
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/excel/sheet")
async def change_sheet(payload: Dict[str, str]):
    """Switches the active worksheet."""
    sheet_name = payload.get("sheet_name")
    if not app_state["excel_path"]:
        raise HTTPException(status_code=400, detail="No Excel file uploaded yet.")

    try:
        df, columns, metadata = ExcelDataLoader.load(app_state["excel_path"], sheet_name)
        app_state["active_sheet"] = sheet_name
        app_state["current_df"] = df
        app_state["current_columns"] = columns
        app_state["current_metadata"] = metadata
        sample_rows = df.head(5).fillna("").to_dict(orient="records")

        return {
            "status": "success",
            "active_sheet": sheet_name,
            "columns": columns,
            "metadata": metadata,
            "total_students": len(df),
            "sample_rows": sample_rows
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload/signature")
async def upload_signature(file: UploadFile = File(...)):
    """Uploads transparent signature PNG."""
    try:
        suffix = Path(file.filename).suffix.lower()
        save_path = UPLOADS_DIR / f"signature{suffix}"
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        app_state["signature_path"] = str(save_path)
        return {
            "status": "success",
            "signature_path": str(save_path),
            "signature_url": f"/uploads/{save_path.name}"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auto-place")
async def auto_place():
    """Generates optimized standard placeholder coordinates."""
    # Use template dimensions if available
    w = 2000.0
    h = 1414.0
    if app_state["front_template_path"] and Path(app_state["front_template_path"]).exists():
        try:
            with Image.open(app_state["front_template_path"]) as img:
                w, h = float(img.width), float(img.height)
        except Exception:
            pass

    cx = w / 2.0
    items = [
        PlaceholderItem(
            name="Name",
            page_index=0,
            x=cx - 600.0,
            y=h * 0.44,
            width=1200.0,
            height=90.0,
            font_family="PTSerif-Bold",
            font_size=54,
            font_color="#112354",
            alignment="center",
            auto_shrink=True
        ),
        PlaceholderItem(
            name="Register No",
            page_index=0,
            x=cx - 300.0,
            y=h * 0.52,
            width=600.0,
            height=70.0,
            font_family="PTSerif-Regular",
            font_size=38,
            font_color="#2b3b55",
            alignment="center",
            auto_shrink=True
        ),
        PlaceholderItem(
            name="Department",
            page_index=0,
            x=cx - 650.0,
            y=h * 0.60,
            width=1300.0,
            height=70.0,
            font_family="PTSerif-Regular",
            font_size=36,
            font_color="#2b3b55",
            alignment="center",
            auto_shrink=True
        ),
        PlaceholderItem(
            name="Dates",
            page_index=0,
            x=cx - 400.0,
            y=h * 0.68,
            width=800.0,
            height=60.0,
            font_family="PTSerif-Regular",
            font_size=32,
            font_color="#334466",
            alignment="center",
            auto_shrink=True
        )
    ]

    if app_state["signature_path"]:
        items.append(
            PlaceholderItem(
                name="Signature",
                page_index=0,
                x=w - 550.0,
                y=h - 320.0,
                width=300.0,
                height=130.0,
                is_signature=True,
                image_path=app_state["signature_path"]
            )
        )

    return {"status": "success", "items": [item.to_dict() for item in items]}


@app.post("/api/preview")
async def generate_preview(req: PreviewRequest):
    """Renders a real-time live preview of a specific student record."""
    try:
        tpl_path = app_state["front_template_path"] if req.page_index == 0 else app_state["back_template_path"]
        if not tpl_path or not Path(tpl_path).exists():
            return JSONResponse({"status": "no_template", "message": "No template uploaded for this page."})

        # Load active row data
        row_data = {}
        if app_state["current_df"] is not None and not app_state["current_df"].empty:
            idx = max(0, min(req.student_index, len(app_state["current_df"]) - 1))
            row_data = app_state["current_df"].iloc[idx].fillna("").to_dict()
            for k, v in app_state["current_metadata"].items():
                if k not in row_data or not row_data[k]:
                    row_data[k] = v

        # Convert request items to PlaceholderItem objects
        items = [PlaceholderItem.from_dict(it.model_dump()) for it in req.items]

        # Build config
        cfg = ProjectConfig(
            page_count=req.page_count,
            front_template_path=app_state["front_template_path"],
            back_template_path=app_state["back_template_path"],
            signature_path=app_state["signature_path"],
            items=items
        )

        gen = CertificateGenerator(cfg)
        with Image.open(tpl_path) as tpl_img:
            rendered = gen.render_page(tpl_img, req.page_index, row_data)
            
            # Create a web-optimized display image (max 1600px width for fast response)
            max_w = 1600
            if rendered.width > max_w:
                ratio = max_w / float(rendered.width)
                disp_img = rendered.resize((max_w, int(rendered.height * ratio)), Image.Resampling.LANCZOS)
            else:
                disp_img = rendered

            buf = io.BytesIO()
            disp_img.save(buf, format="JPEG", quality=88)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

        return {
            "status": "success",
            "preview_b64": f"data:image/jpeg;base64,{b64}",
            "student_index": req.student_index,
            "student_info": {
                "name": str(row_data.get("Name", row_data.get("Student Name", "Sample Student"))),
                "reg_no": str(row_data.get("Register No", row_data.get("Reg No", "12345678"))),
                "department": str(row_data.get("Department", app_state["current_metadata"].get("Department", "")))
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
async def generate_certificates(req: GenerateRequest):
    """Bulk generates certificates and bundles them into a ZIP file."""
    if not app_state["front_template_path"]:
        raise HTTPException(status_code=400, detail="Front page template must be uploaded first.")
    if req.page_count == 2 and not app_state["back_template_path"]:
        raise HTTPException(status_code=400, detail="Back page template must be uploaded for 2-page mode.")
    if app_state["current_df"] is None or app_state["current_df"].empty:
        raise HTTPException(status_code=400, detail="Please upload student data Excel file.")

    try:
        # Clear/prepare output directory
        target_dir = OUTPUT_DIR / "generated"
        target_dir.mkdir(parents=True, exist_ok=True)
        for existing in target_dir.glob("*.pdf"):
            try:
                existing.unlink()
            except Exception:
                pass

        items = [PlaceholderItem.from_dict(it.model_dump()) for it in req.items]
        target_sheet = req.selected_sheet or app_state["active_sheet"]
        cfg = ProjectConfig(
            page_count=req.page_count,
            front_template_path=app_state["front_template_path"],
            back_template_path=app_state["back_template_path"],
            signature_path=app_state["signature_path"],
            excel_data_path=app_state["excel_path"],
            selected_sheet=target_sheet,
            generate_all_sheets=req.generate_all_sheets,
            naming_pattern=req.naming_pattern,
            output_dir=str(target_dir),
            items=items
        )

        gen = CertificateGenerator(cfg)
        generated_pdfs = gen.generate_all()

        # Package into ZIP
        zip_path = OUTPUT_DIR / "certificates_bundle.zip"
        with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for p in generated_pdfs:
                arcname = p.relative_to(target_dir)
                zf.write(p, arcname=str(arcname))

        return {
            "status": "success",
            "total_generated": len(generated_pdfs),
            "sheets_processed": len(app_state["excel_sheets"]) if req.generate_all_sheets else 1,
            "download_zip_url": "/api/download/certificates_bundle.zip",
            "output_directory": str(target_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Serves the generated ZIP archive for direct browser download."""
    fp = OUTPUT_DIR / filename
    if not fp.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(fp),
        filename=filename,
        media_type="application/zip" if filename.endswith(".zip") else "application/pdf"
    )


def open_browser():
    """Opens user's default browser after server start."""
    port = int(os.environ.get("PORT", 8000))
    url = f"http://127.0.0.1:{port}"
    print(f"\n=======================================================")
    print(f"🚀 VISUAL BULK CERTIFICATE GENERATOR (WEB EDITION)")
    print(f"🌐 Local Address:   {url}")
    print(f"🌍 Internet Access: Ready for Cloudflare Tunnel / Ngrok / Render")
    print(f"=======================================================\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    # Support custom port for cloud hosts (Render, Railway, Heroku, Docker)
    port = int(os.environ.get("PORT", 8000))
    # Open local browser if running on desktop
    if not os.environ.get("HEADLESS") and not os.environ.get("PORT"):
        import threading
        threading.Timer(1.2, open_browser).start()

    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
