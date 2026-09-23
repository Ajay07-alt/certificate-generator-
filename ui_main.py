"""
Main desktop user interface for Visual Bulk Certificate Generator.
Constructed with Tkinter and TTK, featuring dual-page canvas tabs,
file upload ribbon, variables list, property inspector, and bulk generation engine.
"""

import os
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image

from models import PlaceholderItem, ProjectConfig
from generator import CertificateGenerator, ExcelDataLoader, sanitize_filename
from canvas_editor import CanvasEditor


class MainWindow(tk.Tk):
    """Primary application window."""

    def __init__(self):
        super().__init__()

        self.title("Visual Bulk Certificate Generator - 2-Page Designer & Automation")
        self.geometry("1340x840")
        self.minsize(1080, 680)

        # Apply system theme styling
        self._setup_styles()

        # Application state
        self.config = ProjectConfig()
        self.excel_data: Optional[Any] = None
        self.available_variables: List[str] = [
            "Name", "Register No", "Department", "From Date", "To Date",
            "Certificate No", "Date of Issue", "Grade Obtained",
            "Student Attendance", "Mini Project Done", "Signature"
        ]
        self.sample_row_data: Dict[str, Any] = {}
        self.is_generating: bool = False
        self.cancel_generation: bool = False
        self.page_count: int = 1

        # Build UI layout
        self._build_top_ribbon()
        self._build_main_body()
        self._build_bottom_panel()

        # Load default project if available
        self._load_initial_defaults()

    def _setup_styles(self):
        self.style = ttk.Style(self)
        # Try clam or default theme for consistent border & button rendering
        available_themes = self.style.theme_names()
        if "clam" in available_themes:
            self.style.theme_use("clam")

        # Configure custom styling
        self.style.configure("TFrame", background="#f3f4f6")
        self.style.configure("TLabel", background="#f3f4f6", font=("Segoe UI", 9))
        self.style.configure("TLabelframe", background="#f3f4f6", font=("Segoe UI", 9, "bold"))
        self.style.configure("TLabelframe.Label", background="#f3f4f6", font=("Segoe UI", 9, "bold"))

        # Buttons
        self.style.configure("TButton", font=("Segoe UI", 9), padding=5)
        self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background="#2563eb", foreground="#ffffff")
        self.style.map("Primary.TButton", background=[("active", "#1d4ed8")])

        self.style.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background="#059669", foreground="#ffffff")
        self.style.map("Success.TButton", background=[("active", "#047857")])

        self.style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), background="#d97706", foreground="#ffffff")

    def _build_top_ribbon(self):
        """Builds top toolbar containing file upload and layout preset buttons."""
        ribbon = ttk.LabelFrame(self, text="  1. Input Files & Layout Presets  ", padding="8 6")
        ribbon.pack(fill="x", padx=10, pady=(6, 4))

        # Page Count Selector
        page_box = ttk.Frame(ribbon)
        page_box.pack(side="left", padx=(2, 6))
        ttk.Label(page_box, text="📄 Pages:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 2))
        self.page_count_combo = ttk.Combobox(
            page_box,
            values=["1 Page (Front Only)", "2 Pages (Front & Back)"],
            width=17,
            state="readonly"
        )
        self.page_count_combo.set("1 Page (Front Only)")
        self.page_count_combo.pack(side="left", padx=2)
        self.page_count_combo.bind("<<ComboboxSelected>>", self._on_page_count_changed)

        # Upload Front
        front_box = ttk.Frame(ribbon)
        front_box.pack(side="left", padx=4)
        self.front_btn = ttk.Button(front_box, text="📄 Front Template", command=self._upload_front_template)
        self.front_btn.pack(side="left")
        self.front_status_lbl = ttk.Label(front_box, text="Not Loaded", foreground="#dc2626", font=("Segoe UI", 8))
        self.front_status_lbl.pack(side="left", padx=4)

        # Upload Back
        self.back_box = ttk.Frame(ribbon)
        self.back_box.pack(side="left", padx=4)
        self.back_btn = ttk.Button(self.back_box, text="📄 Back Template", command=self._upload_back_template)
        self.back_btn.pack(side="left")
        self.back_status_lbl = ttk.Label(self.back_box, text="(1-Page Mode)", foreground="#6b7280", font=("Segoe UI", 8))
        self.back_status_lbl.pack(side="left", padx=4)

        # Upload Excel
        excel_box = ttk.Frame(ribbon)
        excel_box.pack(side="left", padx=6)
        ttk.Button(excel_box, text="📊 Excel Data", command=self._upload_excel_file).pack(side="left")
        self.excel_status_lbl = ttk.Label(excel_box, text="Not Loaded", foreground="#dc2626", font=("Segoe UI", 8))
        self.excel_status_lbl.pack(side="left", padx=4)

        # Excel Page / Sheet Changer Dropdown
        sheet_box = ttk.Frame(ribbon)
        sheet_box.pack(side="left", padx=6)
        ttk.Label(sheet_box, text="📑 Sheet/Page:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(2, 2))
        self.sheet_combo = ttk.Combobox(sheet_box, width=13, state="readonly")
        self.sheet_combo.pack(side="left", padx=2)
        self.sheet_combo.bind("<<ComboboxSelected>>", self._on_sheet_selection_changed)

        # Upload Signature
        sig_box = ttk.Frame(ribbon)
        sig_box.pack(side="left", padx=6)
        ttk.Button(sig_box, text="✒️ Signature", command=self._upload_signature_image).pack(side="left")
        self.sig_status_lbl = ttk.Label(sig_box, text="Not Loaded", foreground="#dc2626", font=("Segoe UI", 8))
        self.sig_status_lbl.pack(side="left", padx=4)

        # Separator
        ttk.Separator(ribbon, orient="vertical").pack(side="left", fill="y", padx=10)

        # Preset Save / Load
        preset_box = ttk.Frame(ribbon)
        preset_box.pack(side="right", padx=6)
        ttk.Button(preset_box, text="💾 Save Layout", command=self._save_layout_preset).pack(side="left", padx=3)
        ttk.Button(preset_box, text="📂 Load Layout", command=self._load_layout_preset).pack(side="left", padx=3)
        ttk.Button(preset_box, text="🔄 Reset Default", command=self._restore_default_preset).pack(side="left", padx=3)

    def _build_main_body(self):
        """Builds central work area: Left Sidebar (Variables & Quick Inspector) + Center Notebook Canvas."""
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=10, pady=4)

        # ----------------- Left Sidebar -----------------
        sidebar = ttk.Frame(body, width=280)
        sidebar.pack(side="left", fill="y", padx=(0, 8))
        sidebar.pack_propagate(False)

        # Available Variables Frame
        vars_frame = ttk.LabelFrame(sidebar, text="  Available Variables  ", padding=6)
        vars_frame.pack(fill="both", expand=True, pady=(0, 6))

        info_lbl = ttk.Label(
            vars_frame,
            text="Select a variable below and click '+ Place on Canvas', or double-click to place:",
            wraplength=250,
            foreground="#4b5563",
            font=("Segoe UI", 8)
        )
        info_lbl.pack(anchor="w", pady=(0, 6))

        # Listbox with Scrollbar
        list_container = ttk.Frame(vars_frame)
        list_container.pack(fill="both", expand=True)

        self.vars_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 9),
            selectmode="single",
            exportselection=False,
            activestyle="none",
            bd=1,
            relief="solid",
            highlightthickness=0
        )
        v_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.vars_listbox.yview)
        self.vars_listbox.configure(yscrollcommand=v_scroll.set)

        self.vars_listbox.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        self.vars_listbox.bind("<Double-Button-1>", lambda e: self._on_place_variable_clicked())

        # Place Button
        place_btn = ttk.Button(
            vars_frame,
            text="➕ Place on Active Canvas",
            style="Primary.TButton",
            command=self._on_place_variable_clicked
        )
        place_btn.pack(fill="x", pady=(6, 2))

        # Quick Selected Item Inspector Frame
        self.inspector_frame = ttk.LabelFrame(sidebar, text="  Selected Placeholder  ", padding=6)
        self.inspector_frame.pack(fill="x", pady=(4, 0))

        self.sel_name_lbl = ttk.Label(self.inspector_frame, text="No item selected", font=("Segoe UI", 9, "bold"))
        self.sel_name_lbl.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)

        ttk.Label(self.inspector_frame, text="Font Size:").grid(row=1, column=0, sticky="w", pady=2)
        self.quick_size_spin = ttk.Spinbox(self.inspector_frame, from_=10, to=160, width=6, command=self._quick_size_changed)
        self.quick_size_spin.grid(row=1, column=1, sticky="w", padx=4, pady=2)
        self.quick_size_spin.bind("<Return>", lambda e: self._quick_size_changed())

        ttk.Label(self.inspector_frame, text="Align:").grid(row=2, column=0, sticky="w", pady=2)
        align_row = ttk.Frame(self.inspector_frame)
        align_row.grid(row=2, column=1, sticky="w", padx=4, pady=2)
        self.quick_align_var = tk.StringVar(value="center")
        ttk.Radiobutton(align_row, text="L", value="left", variable=self.quick_align_var, command=self._quick_align_changed).pack(side="left")
        ttk.Radiobutton(align_row, text="C", value="center", variable=self.quick_align_var, command=self._quick_align_changed).pack(side="left")
        ttk.Radiobutton(align_row, text="R", value="right", variable=self.quick_align_var, command=self._quick_align_changed).pack(side="left")

        quick_btn_box = ttk.Frame(self.inspector_frame)
        quick_btn_box.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(6, 2))
        ttk.Button(quick_btn_box, text="⚙️ Full Inspector", command=self._open_full_inspector).pack(side="left", expand=True, fill="x", padx=1)
        ttk.Button(quick_btn_box, text="🗑️ Delete", command=self._quick_delete_selected).pack(side="left", expand=True, fill="x", padx=1)

        # ----------------- Center Notebook (Front / Back Canvas) -----------------
        center_frame = ttk.Frame(body)
        center_frame.pack(side="right", fill="both", expand=True)

        self.notebook = ttk.Notebook(center_frame)
        self.notebook.pack(fill="both", expand=True)

        # Front Page Canvas (Page 1)
        self.canvas_front = CanvasEditor(
            self.notebook,
            page_index=0,
            on_items_changed=self._on_canvas_items_changed,
            on_selection_changed=self._on_item_selection_changed
        )
        self.notebook.add(self.canvas_front, text="  📄 Front Page (Page 1)  ")

        # Back Page Canvas (Page 2) - initially prepared, added dynamically based on page count
        self.canvas_back = CanvasEditor(
            self.notebook,
            page_index=1,
            on_items_changed=self._on_canvas_items_changed,
            on_selection_changed=self._on_item_selection_changed
        )

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_switched)

    def _build_bottom_panel(self):
        """Builds bottom generation controls, progress bar, and status output."""
        panel = ttk.LabelFrame(self, text="  2. Output Settings & Bulk Generation  ", padding="8 6")
        panel.pack(fill="x", padx=10, pady=(2, 8))

        # Top row: Output folder & naming pattern
        row1 = ttk.Frame(panel)
        row1.pack(fill="x", pady=2)

        ttk.Label(row1, text="Output Directory:").pack(side="left", padx=(0, 4))
        self.out_dir_var = tk.StringVar(value=str(Path("./output_certificates").resolve()))
        out_entry = ttk.Entry(row1, textvariable=self.out_dir_var)
        out_entry.pack(side="left", fill="x", expand=True, padx=4)

        ttk.Button(row1, text="Browse...", command=self._browse_output_dir).pack(side="left", padx=4)
        ttk.Button(row1, text="📂 Open Folder", command=self._open_output_dir).pack(side="left", padx=4)

        # Bottom row: Progress bar + Scope + Generate button
        row2 = ttk.Frame(panel)
        row2.pack(fill="x", pady=(6, 2))

        self.progress_bar = ttk.Progressbar(row2, orient="horizontal", mode="determinate")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.status_lbl = ttk.Label(row2, text="Ready. Templates and data loaded.", foreground="#374151")
        self.status_lbl.pack(side="left", padx=(0, 10))

        # Scope Checkbox
        self.gen_all_sheets_var = tk.BooleanVar(value=False)
        self.gen_all_cb = ttk.Checkbutton(
            row2,
            text="📑 Batch ALL Sheets in Workbook",
            variable=self.gen_all_sheets_var
        )
        self.gen_all_cb.pack(side="right", padx=(6, 12))

        self.generate_btn = ttk.Button(
            row2,
            text="⚡ GENERATE CERTIFICATES",
            style="Success.TButton",
            command=self._start_generation
        )
        self.generate_btn.pack(side="right")

    # -------------------------------------------------------------
    # Page Count Controller
    # -------------------------------------------------------------

    def _on_page_count_changed(self, event=None):
        val = self.page_count_combo.get()
        count = 1 if "1" in val else 2
        self.set_page_count(count)

    def set_page_count(self, count: int):
        """Dynamically adjusts the certificate page count (1: Front only, 2: Front & Back)."""
        self.page_count = count
        self.config.page_count = count

        if count == 1:
            self.page_count_combo.set("1 Page (Front Only)")
            try:
                self.notebook.forget(self.canvas_back)
            except Exception:
                pass
            self.back_btn.configure(state="disabled")
            if not self.config.back_template_path:
                self.back_status_lbl.configure(text="(1-Page Mode)", foreground="#6b7280")
            self.notebook.select(0)
            self.status_lbl.configure(text="Configured for 1 Page (Front Only). Single-page PDFs will be generated.")
        else:
            self.page_count_combo.set("2 Pages (Front & Back)")
            tabs = self.notebook.tabs()
            if str(self.canvas_back) not in tabs:
                self.notebook.add(self.canvas_back, text="  📄 Back Page (Page 2)  ")
            self.back_btn.configure(state="normal")
            if self.config.back_template_path and Path(self.config.back_template_path).exists():
                self.back_status_lbl.configure(text="✓ Loaded", foreground="#059669")
            else:
                self.back_status_lbl.configure(text="Not Loaded", foreground="#dc2626")
            self.status_lbl.configure(text="Configured for 2 Pages (Front & Back). Two-page PDFs will be generated.")

    # -------------------------------------------------------------
    # Initial Defaults Loader
    # -------------------------------------------------------------

    def _load_initial_defaults(self):
        """Initializes application state with clean templates and editable 1-page default."""
        self.page_count = 1
        self.config.page_count = 1
        self.config.front_template_path = ""
        self.config.back_template_path = ""
        self.config.items = []

        base_dir = Path(__file__).resolve().parent
        sample_xlsx = base_dir / "assets" / "robotics_lab_data.xlsx"
        if not sample_xlsx.exists():
            sample_xlsx = base_dir / "assets" / "sample_data.xlsx"

        sample_sig = base_dir / "assets" / "sample_signature.png"

        # Apply 1-page mode initially
        self.set_page_count(1)

        # Pre-load Excel data so available variables list is immediately populated
        if sample_xlsx.exists():
            self._process_excel_file(str(sample_xlsx.resolve()))

        # Pre-load sample signature if present
        if sample_sig.exists():
            self.config.signature_path = str(sample_sig.resolve())
            self.sig_status_lbl.configure(text="✓ Loaded", foreground="#059669")

        # Canvases start clean with NO default templates forced
        self.front_status_lbl.configure(text="Not Loaded", foreground="#dc2626")
        self.back_status_lbl.configure(text="(1-Page Mode)", foreground="#6b7280")
        self.status_lbl.configure(text="Ready. Please upload your certificate template (PNG, JPG, or PDF).")

    def _sync_items_to_canvases(self):
        front_items = [it for it in self.config.items if it.page_index == 0]
        back_items = [it for it in self.config.items if it.page_index == 1]
        self.canvas_front.set_items(front_items)
        self.canvas_back.set_items(back_items)

    def _sync_items_from_canvases(self):
        self.config.items = self.canvas_front.items + self.canvas_back.items

    def _get_active_canvas(self) -> CanvasEditor:
        selected_tab = self.notebook.index(self.notebook.select())
        return self.canvas_front if selected_tab == 0 else self.canvas_back

    # -------------------------------------------------------------
    # Input Handlers (Buttons)
    # -------------------------------------------------------------

    def _upload_front_template(self):
        path = filedialog.askopenfilename(
            title="Select Front Page Template Image (or PDF)",
            filetypes=[("Images & PDFs", "*.png *.jpg *.jpeg *.pdf"), ("PNG Images", "*.png"), ("PDF Files", "*.pdf")]
        )
        if not path:
            return

        if path.lower().endswith(".pdf"):
            try:
                import pymupdf
                doc = pymupdf.open(path)
                num_pages = len(doc)
                doc.close()

                if num_pages >= 2 and self.page_count == 1:
                    res = messagebox.askyesno(
                        "Multi-Page Certificate Detected",
                        f"The selected PDF contains {num_pages} pages.\n\n"
                        "Would you like to set Certificate Pages to 2 and automatically import:\n"
                        "• Page 1 as Front Page Template\n"
                        "• Page 2 as Back Page Template?"
                    )
                    if res:
                        self.set_page_count(2)
                        p1_img = self._convert_pdf_page_to_image(path, page_idx=0, output_prefix="front_template")
                        p2_img = self._convert_pdf_page_to_image(path, page_idx=1, output_prefix="back_template")
                        self.config.front_template_path = p1_img
                        self.config.back_template_path = p2_img
                        self.canvas_front.set_template_image(p1_img)
                        self.canvas_back.set_template_image(p2_img)
                        self.front_status_lbl.configure(text="✓ Loaded", foreground="#059669")
                        self.back_status_lbl.configure(text="✓ Loaded", foreground="#059669")
                        self.status_lbl.configure(text=f"Loaded Front and Back templates from {Path(path).name}")
                        return
            except Exception as e:
                print(f"Notice: Could not inspect PDF page count: {e}")

            # Extract Page 1 from PDF
            path = self._convert_pdf_page_to_image(path, page_idx=0, output_prefix="front_template")

        self.config.front_template_path = path
        self.canvas_front.set_template_image(path)
        self.front_status_lbl.configure(text="✓ Loaded", foreground="#059669")
        self.notebook.select(0)  # switch to front tab

    def _upload_back_template(self):
        path = filedialog.askopenfilename(
            title="Select Back Page Template Image (or PDF)",
            filetypes=[("Images & PDFs", "*.png *.jpg *.jpeg *.pdf"), ("PNG Images", "*.png"), ("PDF Files", "*.pdf")]
        )
        if not path:
            return

        if path.lower().endswith(".pdf"):
            # Extract Page 2 from PDF (or page 1 if only 1 page)
            path = self._convert_pdf_page_to_image(path, page_idx=1, output_prefix="back_template")

        self.config.back_template_path = path
        self.canvas_back.set_template_image(path)
        self.back_status_lbl.configure(text="✓ Loaded", foreground="#059669")
        self.notebook.select(1)  # switch to back tab

    def _convert_pdf_page_to_image(self, pdf_path: str, page_idx: int, output_prefix: str) -> str:
        """Helper to render high-res 300 DPI PNG from PDF page."""
        try:
            import pymupdf
            doc = pymupdf.open(pdf_path)
            idx = min(page_idx, len(doc) - 1)
            page = doc[idx]
            pix = page.get_pixmap(dpi=300)
            out_img = Path(pdf_path).parent / f"{output_prefix}_{idx+1}.png"
            pix.save(str(out_img))
            doc.close()
            return str(out_img.resolve())
        except Exception as e:
            messagebox.showerror("PDF Render Error", f"Could not render PDF page: {e}")
            return pdf_path

    def _upload_excel_file(self):
        path = filedialog.askopenfilename(
            title="Select Student Data Excel File",
            filetypes=[("Excel Files", "*.xlsx *.xls *.csv"), ("All Files", "*.*")]
        )
        if not path:
            return
        self._process_excel_file(path)

    def _on_sheet_selection_changed(self, event=None):
        selected_sheet = self.sheet_combo.get().strip()
        if self.config.excel_data_path and selected_sheet:
            self._process_excel_file(self.config.excel_data_path, target_sheet=selected_sheet)

    def _process_excel_file(self, path: str, target_sheet: Optional[str] = None):
        try:
            self.config.excel_data_path = path

            # 1. Fetch available sheets/pages in workbook
            sheet_names = ExcelDataLoader.get_sheet_names(path)
            self.sheet_combo["values"] = sheet_names

            if target_sheet and target_sheet in sheet_names:
                current_sheet = target_sheet
            elif self.config.selected_sheet and self.config.selected_sheet in sheet_names:
                current_sheet = self.config.selected_sheet
            elif sheet_names:
                current_sheet = sheet_names[0]
            else:
                current_sheet = None

            if current_sheet:
                self.sheet_combo.set(current_sheet)
                self.config.selected_sheet = current_sheet

            # 2. Load the specific sheet
            df, cols, metadata = ExcelDataLoader.load(path, sheet_name=current_sheet)
            self.excel_data = df

            # Update Available Variables
            unique_vars = []
            for c in cols:
                if c not in unique_vars:
                    unique_vars.append(c)
            # Add signature tag
            if "Signature" not in unique_vars:
                unique_vars.append("Signature")

            self.available_variables = unique_vars

            # Refresh Listbox
            self.vars_listbox.delete(0, tk.END)
            for v in self.available_variables:
                self.vars_listbox.insert(tk.END, f"  🏷️ {v}")

            # Send available variables to canvases
            self.canvas_front.set_available_variables(self.available_variables)
            self.canvas_back.set_available_variables(self.available_variables)

            # Pass all rows to canvases for student navigator
            rows_list = df.to_dict("records")
            self.canvas_front.set_all_rows(rows_list)
            self.canvas_back.set_all_rows(rows_list)

            dept_info = f" ({metadata['Department']})" if "Department" in metadata and metadata["Department"] else ""
            sheet_disp = f"'{current_sheet}'" if current_sheet else "Sheet"
            self.excel_status_lbl.configure(text=f"✓ {sheet_disp} ({len(df)} rows)", foreground="#059669")
            self.status_lbl.configure(text=f"Loaded sheet {sheet_disp} with {len(df)} students{dept_info}")

        except Exception as e:
            messagebox.showerror("Excel Ingestion Error", f"Failed to parse Excel file:\n{e}")

    def _upload_signature_image(self):
        path = filedialog.askopenfilename(
            title="Select Transparent Signature Image",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg"), ("PNG Transparent", "*.png")]
        )
        if not path:
            return

        self.config.signature_path = path
        self.sig_status_lbl.configure(text="✓ Loaded", foreground="#059669")
        messagebox.showinfo(
            "Signature Ready",
            f"Signature image loaded!\n\nTo place it on the canvas, select 'Signature' from the left sidebar and click '+ Place on Active Canvas'."
        )

    def _browse_output_dir(self):
        folder = filedialog.askdirectory(title="Select Output Folder for Certificates")
        if folder:
            self.out_dir_var.set(folder)
            self.config.output_dir = folder

    def _open_output_dir(self):
        out = Path(self.out_dir_var.get())
        out.mkdir(parents=True, exist_ok=True)
        os.startfile(str(out))

    # -------------------------------------------------------------
    # Presets Save / Load
    # -------------------------------------------------------------

    def _save_layout_preset(self):
        self._sync_items_from_canvases()
        path = filedialog.asksaveasfilename(
            title="Save Layout Preset",
            defaultextension=".json",
            filetypes=[("JSON Layout Preset", "*.json")]
        )
        if not path:
            return

        self.config.output_dir = self.out_dir_var.get()
        self.config.save_to_json(path)
        messagebox.showinfo("Preset Saved", f"Layout configuration saved to:\n{path}")

    def _load_layout_preset(self):
        path = filedialog.askopenfilename(
            title="Load Layout Preset",
            filetypes=[("JSON Layout Preset", "*.json")]
        )
        if not path:
            return

        try:
            self.config = ProjectConfig.load_from_json(path)
            self.set_page_count(self.config.page_count)

            if self.config.output_dir:
                self.out_dir_var.set(self.config.output_dir)

            if self.config.front_template_path and Path(self.config.front_template_path).exists():
                self.canvas_front.set_template_image(self.config.front_template_path)
                self.front_status_lbl.configure(text="✓ Loaded", foreground="#059669")
            else:
                self.front_status_lbl.configure(text="Not Loaded", foreground="#dc2626")

            if self.page_count >= 2:
                if self.config.back_template_path and Path(self.config.back_template_path).exists():
                    self.canvas_back.set_template_image(self.config.back_template_path)
                    self.back_status_lbl.configure(text="✓ Loaded", foreground="#059669")
                else:
                    self.back_status_lbl.configure(text="Not Loaded", foreground="#dc2626")

            if self.config.signature_path and Path(self.config.signature_path).exists():
                self.sig_status_lbl.configure(text="✓ Loaded", foreground="#059669")

            if self.config.excel_data_path and Path(self.config.excel_data_path).exists():
                self._process_excel_file(self.config.excel_data_path)

            self._sync_items_to_canvases()
            messagebox.showinfo("Preset Loaded", f"Successfully loaded preset from:\n{path}\nPages: {self.page_count}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load layout preset:\n{e}")

    def _restore_default_preset(self):
        base_dir = Path(__file__).resolve().parent
        default_layout_path = base_dir / "assets" / "default_layout.json"
        if default_layout_path.exists():
            self.config = ProjectConfig.load_from_json(str(default_layout_path))
            self.set_page_count(self.config.page_count)
            if self.config.front_template_path and Path(self.config.front_template_path).exists():
                self.canvas_front.set_template_image(self.config.front_template_path)
                self.front_status_lbl.configure(text="✓ Loaded", foreground="#059669")
            if self.config.back_template_path and Path(self.config.back_template_path).exists():
                self.canvas_back.set_template_image(self.config.back_template_path)
                self.back_status_lbl.configure(text="✓ Loaded", foreground="#059669")
            if self.config.excel_data_path and Path(self.config.excel_data_path).exists():
                self._process_excel_file(self.config.excel_data_path)
            self._sync_items_to_canvases()
            self.status_lbl.configure(text=f"Default Robotics Lab layout restored ({self.page_count} pages).")

    # -------------------------------------------------------------
    # Visual Canvas Interactions
    # -------------------------------------------------------------

    def _on_place_variable_clicked(self):
        sel = self.vars_listbox.curselection()
        if not sel:
            messagebox.showwarning("Select Variable", "Please click on a variable from the list first.")
            return

        var_text = self.vars_listbox.get(sel[0]).replace("🏷️", "").strip()
        active_canvas = self._get_active_canvas()
        active_canvas.start_placement_mode(var_text)

    def _on_canvas_items_changed(self):
        self._sync_items_from_canvases()

    def _on_item_selection_changed(self, item: Optional[PlaceholderItem]):
        if item:
            self.sel_name_lbl.configure(text=f"Selected: {item.name[:18]}")
            self.quick_size_spin.set(str(item.font_size))
            self.quick_align_var.set(item.alignment)
        else:
            self.sel_name_lbl.configure(text="No item selected")

    def _quick_size_changed(self):
        canvas = self._get_active_canvas()
        if canvas.selected_item and not canvas.selected_item.is_signature:
            try:
                new_size = int(self.quick_size_spin.get())
                canvas.selected_item.font_size = new_size
                canvas.refresh_canvas()
                self._sync_items_from_canvases()
            except ValueError:
                pass

    def _quick_align_changed(self):
        canvas = self._get_active_canvas()
        if canvas.selected_item and not canvas.selected_item.is_signature:
            canvas.selected_item.alignment = self.quick_align_var.get()
            canvas.refresh_canvas()
            self._sync_items_from_canvases()

    def _open_full_inspector(self):
        canvas = self._get_active_canvas()
        if canvas.selected_item:
            canvas.open_item_inspector(canvas.selected_item)

    def _quick_delete_selected(self):
        canvas = self._get_active_canvas()
        if canvas.selected_item:
            canvas._on_inspector_delete(canvas.selected_item)

    def _on_tab_switched(self, event):
        active_canvas = self._get_active_canvas()
        active_canvas.refresh_canvas()

    # -------------------------------------------------------------
    # Bulk Generation Engine
    # -------------------------------------------------------------

    def _start_generation(self):
        if self.is_generating:
            return

        # Synchronize items and options
        self._sync_items_from_canvases()
        self.config.output_dir = self.out_dir_var.get()
        self.config.generate_all_sheets = self.gen_all_sheets_var.get()
        self.config.selected_sheet = self.sheet_combo.get().strip()

        # Validation
        self.config.page_count = self.page_count
        if not self.config.front_template_path or not Path(self.config.front_template_path).exists():
            messagebox.showerror("Missing Template", "Please upload the Front Page (Page 1) template image.")
            return
        if self.page_count >= 2:
            if not self.config.back_template_path or not Path(self.config.back_template_path).exists():
                messagebox.showerror("Missing Template", "Please upload the Back Page (Page 2) template image, or switch Certificate Pages to 1.")
                return
        if not self.config.excel_data_path or not Path(self.config.excel_data_path).exists():
            messagebox.showerror("Missing Data", "Please upload the Excel data file.")
            return

        # Prepare UI
        self.is_generating = True
        self.cancel_generation = False
        self.generate_btn.configure(state="disabled")
        self.progress_bar.configure(value=0)
        self.status_lbl.configure(text="Generating certificates in background...", foreground="#2563eb")

        # Launch worker thread so the UI remains fluid
        t = threading.Thread(target=self._generation_worker, daemon=True)
        t.start()

    def _generation_worker(self):
        try:
            generator = CertificateGenerator(self.config)

            def progress_callback(cur: int, total: int, filename: str):
                self.after(0, lambda: self._update_progress(cur, total, filename))

            def cancel_check():
                return self.cancel_generation

            generated_files = generator.generate_all(
                progress_callback=progress_callback,
                cancel_check=cancel_check
            )

            self.after(0, lambda: self._on_generation_finished(generated_files))

        except Exception as e:
            self.after(0, lambda: self._on_generation_error(str(e)))

    def _update_progress(self, cur: int, total: int, filename: str):
        pct = (cur / float(total)) * 100.0
        self.progress_bar.configure(value=pct)
        self.status_lbl.configure(
            text=f"Generated [{cur}/{total}]: {filename}",
            foreground="#2563eb"
        )

    def _on_generation_finished(self, files: List[Path]):
        self.is_generating = False
        self.generate_btn.configure(state="normal")
        self.progress_bar.configure(value=100)
        count = len(files)
        out_folder = self.out_dir_var.get()

        self.status_lbl.configure(
            text=f"✓ Complete! Generated {count} certificates in {Path(out_folder).name}",
            foreground="#059669"
        )

        res = messagebox.askyesno(
            "Generation Complete!",
            f"Successfully generated {count} two-page certificate PDFs!\n\nLocation: {out_folder}\n\nWould you like to open the output folder now?"
        )
        if res:
            self._open_output_dir()

    def _on_generation_error(self, err_msg: str):
        self.is_generating = False
        self.generate_btn.configure(state="normal")
        self.status_lbl.configure(text="Generation failed.", foreground="#dc2626")
        messagebox.showerror("Generation Error", f"An error occurred during certificate generation:\n\n{err_msg}")
