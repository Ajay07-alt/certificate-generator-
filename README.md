# Visual Bulk Certificate Generator

An interactive desktop application built in Python for visually designing, positioning, formatting, and bulk-generating two-page certificates (Front & Back) with Excel data mapping, transparent signature stamping, and high-resolution PDF compilation.

---

## Key Features

1. **Interactive Visual Canvas & Page Count Management**:
   - **Editable Certificate Page Count**: Select between **1 Page (Front Only)** and **2 Pages (Front & Back)** using the top ribbon dropdown.
     - **Count = 1**: Displays only the Front Page canvas, disables Page 2, and outputs single-page PDFs.
     - **Count = 2**: Dynamically mounts the Back Page canvas tab, enables Front and Back template uploads, and outputs two-page PDFs.
     - **Smart Multi-Page PDF Detection**: Automatically detects 2-page template PDFs upon upload and prompts to configure both pages simultaneously.
   - **Clean Default Slate**: Launches with clean canvases (no default template images forced) ready for custom user templates. Default layouts can still be loaded on-demand.
   - **Multi-Page Tab Switcher**: Seamlessly switch between active pages (`Front Page` / `Back Page`).
   - **Smooth Zoom & Pan**: Mouse wheel zoom (`Ctrl + Scroll`), zoom in/out buttons, fit to window, and 100% scale.
   - **Click-to-Place / Drag-to-Reposition**: Select any variable from the Excel sheet and place it anywhere on the canvas. Drag to move it freely.
   - **Interactive 8-Point Resize Handles**: 8-point boundary handles (NW, NE, SW, SE, etc.) to resize text boxes and signature stamps.
   - **Double-Click Inspector**: Customize font family (PTSerif, Poppins, NotoSans, Unicode/Tamil), font size, text color (with color picker dialog), text alignment (Left, Center, Right), and prefix/suffix text.
   - **Live Sample Preview**: Toggle between placeholder tags (`[Name]`) and real student data from Row 1 of your Excel file (`AJAY.V`) directly on the canvas.
   - **Multi-Sheet Batch Generation**: Option to generate certificates for just the active sheet or batch generate all 10+ department sheets at once into organized subfolders (`output_certificates/AIML/`, `output_certificates/CSE/`, etc.).

2. **Input File Handling**:
   - **Front & Back Templates**: Upload `.png`, `.jpg`, or directly import pages from `.pdf` certificates.
   - **Excel Student Data**: Reads both standard tables and academic attendance sheets (auto-detects title blocks, attendance percentages, student register numbers).
   - **Signature Upload**: Upload transparent signature PNGs to place and stamp onto certificates.

3. **Resolution-Aware Generation Engine**:
   - Accurately converts screen canvas coordinates to full-resolution 300 DPI image pixels.
   - Pillow (PIL) high-DPI text drawing with auto-shrink to fit long student names without clipping.
   - High-quality signature overlay using Lanczos resampling and alpha compositing.
   - Automatically exports two-page PDFs into the output directory with dynamic student filenames (`{Register_No}_{Name}.pdf`).
   - Threaded background worker prevents UI freezing during bulk processing with live progress bar.

4. **Layout Presets**:
   - Save custom layouts to `.json` files and reload them anytime.
   - Ships with a pre-configured preset for the **Robotics and Automation Lab Certificate** (`Copy of robotics lab certificate.docx` / `.pdf`).

---

## File Structure

```text
1111/
├── assets/
│   ├── default_layout.json     # Pre-tuned field coordinates & typography
│   ├── front_template.png      # 300 DPI Front Page template
│   ├── back_template.png       # 300 DPI Back Page template
│   ├── sample_signature.png    # Transparent signature sample
│   ├── sample_data.xlsx        # Sample student data
│   ├── robotics_lab_data.xlsx  # Raw lab attendance data
│   └── fonts/                  # TrueType fonts (PTSerif, Poppins, NotoSansTamil)
├── models.py                   # Data models for placeholders and configurations
├── generator.py                # Excel ingestion, coordinate mapping & PDF generator
├── canvas_editor.py            # Interactive Tkinter Canvas with handles and inspector
├── ui_main.py                  # Main desktop GUI window
├── main.py                     # Entry point with Windows DPI awareness
├── run_app.bat                 # 1-click Windows launcher
└── README.md                   # Documentation
```

---

## Getting Started

### Prerequisites
Python 3.10+ (tested on Python 3.13) with the following packages installed:
```bash
pip install pandas openpyxl pillow pymupdf
```

### Launching the Application

#### Option 1: Web Edition (In Browser)
Double-click `Launch in Browser.bat` (or run `python server.py`).
Your default web browser will automatically open to `http://127.0.0.1:8000`.

#### Option 2: Desktop Edition (Native GUI Window)
Double-click `Launch Certificate Generator.lnk` or `run_app.bat` (or run `python main.py`).

---

## Launching on the Internet

### Method 1: Instant Free Public HTTPS Link (Cloudflare Tunnel)
To instantly share your running web generator with anyone in the world without signing up or setting up a server:
1. Double-click `Share to Internet (Cloudflare).bat`.
2. A free public HTTPS link (e.g. `https://random-name.trycloudflare.com`) will appear in the window.
3. Share that URL with anyone — they can access the generator from anywhere on mobile or desktop!

### Method 2: 24/7 Cloud Hosting (Render.com / Railway / Hugging Face)
1. Push this project folder to a GitHub repository.
2. Sign up on [Render.com](https://render.com) (Free tier) or [Railway.app](https://railway.app).
3. Create a **New Web Service** and link your GitHub repository.
4. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Render deploys your application 24/7 with a free public URL (e.g. `https://your-cert-generator.onrender.com`).

---

## Quick Workflow

1. **Launch**: Open either the Desktop App or Web App in Browser.
2. **Page Count**: Choose `1 Page (Front Only)` or `2 Pages (Front & Back)`.
3. **Upload Files**: Upload your certificate template, Excel student file, and optional transparent signature.
4. **Edit Layout**:
   - Drag placeholders and adjust bounding boxes with resize handles.
   - Set fonts, colors, auto-shrink, and alignments.
5. **Preview**: Switch students with `◀ Prev` / `Next ▶` to verify alignment on actual student records.
6. **Generate**: Click **"🚀 Generate Certificates"** to compile high-resolution 300 DPI PDFs. Download individual PDFs or the zipped bundle!
