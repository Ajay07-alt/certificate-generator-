"""
Interactive Canvas Editor for the Visual Bulk Certificate Generator.
Provides an interactive Tkinter Canvas for placing, dragging, resizing,
and styling placeholders and signatures directly over the template.
"""

import tkinter as tk
from tkinter import ttk, colorchooser
from typing import Callable, Dict, List, Optional, Tuple, Any
from pathlib import Path
from PIL import Image, ImageTk, ImageFont, ImageDraw

from models import PlaceholderItem

HANDLE_SIZE = 8
HANDLE_POSITIONS = ["nw", "n", "ne", "e", "se", "s", "sw", "w"]
CURSOR_MAP = {
    "nw": "size_nw_se",
    "se": "size_nw_se",
    "ne": "size_ne_sw",
    "sw": "size_ne_sw",
    "n": "size_ns",
    "s": "size_ns",
    "w": "size_we",
    "e": "size_we",
}

class ItemPropertiesDialog(tk.Toplevel):
    """Modal dialog to adjust font family, size, color, alignment, and deletion."""

    def __init__(self, parent, item: PlaceholderItem, available_variables: List[str], on_update: Callable, on_delete: Callable):
        super().__init__(parent)
        self.item = item
        self.available_variables = available_variables
        self.on_update = on_update
        self.on_delete = on_delete

        self.title(f"Edit Placeholder: {item.name}")
        self.geometry("440x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()
        self.center_on_parent(parent)

    def center_on_parent(self, parent):
        self.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w = self.winfo_width()
        h = self.winfo_height()
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        container = ttk.Frame(self, padding="16")
        container.pack(fill="both", expand=True)

        # Header
        title_lbl = ttk.Label(
            container,
            text=f"Formatting: {self.item.name}",
            font=("Segoe UI", 12, "bold")
        )
        title_lbl.pack(anchor="w", pady=(0, 14))

        # Variable Name
        var_frame = ttk.LabelFrame(container, text="Data Mapping", padding=8)
        var_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(var_frame, text="Variable / Column:").grid(row=0, column=0, sticky="w", pady=4)
        self.var_combo = ttk.Combobox(var_frame, values=self.available_variables)
        self.var_combo.set(self.item.name)
        self.var_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=4)
        var_frame.columnconfigure(1, weight=1)

        # Type (Text or Signature)
        self.sig_var = tk.BooleanVar(value=self.item.is_signature)
        sig_cb = ttk.Checkbutton(var_frame, text="Is Signature Stamp", variable=self.sig_var, command=self._toggle_sig_options)
        sig_cb.grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        # Typography Frame
        self.typo_frame = ttk.LabelFrame(container, text="Typography & Appearance", padding=8)
        self.typo_frame.pack(fill="x", pady=(0, 10))
        self.typo_frame.columnconfigure(1, weight=1)

        # Font Family
        ttk.Label(self.typo_frame, text="Font Family:").grid(row=0, column=0, sticky="w", pady=4)
        fonts = ["PTSerif-Bold", "Poppins-Bold", "Poppins-Regular", "NotoSans-Bold", "NotoSans-Regular", "NotoSansTamil-Bold", "Arial", "Times New Roman"]
        self.font_combo = ttk.Combobox(self.typo_frame, values=fonts, state="readonly")
        if self.item.font_family in fonts:
            self.font_combo.set(self.item.font_family)
        else:
            self.font_combo.set(fonts[0])
        self.font_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=4)

        # Font Size
        ttk.Label(self.typo_frame, text="Font Size:").grid(row=1, column=0, sticky="w", pady=4)
        self.size_spin = ttk.Spinbox(self.typo_frame, from_=10, to=200, width=8)
        self.size_spin.set(str(self.item.font_size))
        self.size_spin.grid(row=1, column=1, sticky="w", padx=8, pady=4)

        # Color
        ttk.Label(self.typo_frame, text="Text Color:").grid(row=2, column=0, sticky="w", pady=4)
        color_box = ttk.Frame(self.typo_frame)
        color_box.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        self.color_preview = tk.Label(color_box, bg=self.item.font_color, width=4, relief="ridge")
        self.color_preview.pack(side="left", padx=(0, 6))

        self.color_hex_lbl = ttk.Label(color_box, text=self.item.font_color)
        self.color_hex_lbl.pack(side="left", padx=(0, 8))

        pick_btn = ttk.Button(color_box, text="Choose...", width=9, command=self._pick_color)
        pick_btn.pack(side="left")

        # Alignment
        ttk.Label(self.typo_frame, text="Alignment:").grid(row=3, column=0, sticky="w", pady=4)
        align_box = ttk.Frame(self.typo_frame)
        align_box.grid(row=3, column=1, sticky="w", padx=8, pady=4)

        self.align_var = tk.StringVar(value=self.item.alignment)
        ttk.Radiobutton(align_box, text="Left", value="left", variable=self.align_var).pack(side="left", padx=4)
        ttk.Radiobutton(align_box, text="Center", value="center", variable=self.align_var).pack(side="left", padx=4)
        ttk.Radiobutton(align_box, text="Right", value="right", variable=self.align_var).pack(side="left", padx=4)

        # Auto shrink checkbox
        self.shrink_var = tk.BooleanVar(value=self.item.auto_shrink)
        shrink_cb = ttk.Checkbutton(self.typo_frame, text="Auto-shrink text if exceeding box width", variable=self.shrink_var)
        shrink_cb.grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        # Buttons
        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x", side="bottom", pady=(12, 0))

        del_btn = ttk.Button(btn_bar, text="🗑️ Delete Item", command=self._delete_item)
        del_btn.pack(side="left")

        save_btn = ttk.Button(btn_bar, text="Save & Apply", command=self._save_changes)
        save_btn.pack(side="right")

        cancel_btn = ttk.Button(btn_bar, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="right", padx=6)

        self._toggle_sig_options()

    def _toggle_sig_options(self):
        is_sig = self.sig_var.get()
        state = "disabled" if is_sig else "normal"
        for child in self.typo_frame.winfo_children():
            try:
                child.configure(state=state)
            except Exception:
                pass

    def _pick_color(self):
        chosen = colorchooser.askcolor(color=self.color_hex_lbl.cget("text"), parent=self)
        if chosen and chosen[1]:
            hex_color = chosen[1]
            self.color_preview.configure(bg=hex_color)
            self.color_hex_lbl.configure(text=hex_color)

    def _save_changes(self):
        self.item.name = self.var_combo.get().strip() or self.item.name
        self.item.is_signature = self.sig_var.get()
        if not self.item.is_signature:
            self.item.font_family = self.font_combo.get()
            try:
                self.item.font_size = int(self.size_spin.get())
            except ValueError:
                pass
            self.item.font_color = self.color_hex_lbl.cget("text")
            self.item.alignment = self.align_var.get()
            self.item.auto_shrink = self.shrink_var.get()

        self.on_update(self.item)
        self.destroy()

    def _delete_item(self):
        self.on_delete(self.item)
        self.destroy()


class CanvasEditor(ttk.Frame):
    """
    Interactive scalable canvas view for displaying certificate templates,
    placing placeholders, dragging, resizing, and inspecting elements.
    """

    def __init__(
        self,
        parent,
        page_index: int,
        on_items_changed: Optional[Callable[[], None]] = None,
        on_selection_changed: Optional[Callable[[Optional[PlaceholderItem]], None]] = None
    ):
        super().__init__(parent)
        self.page_index = page_index
        self.on_items_changed = on_items_changed
        self.on_selection_changed = on_selection_changed

        self.template_path: Optional[str] = None
        self.orig_image: Optional[Image.Image] = None
        self.rendered_preview: Optional[ImageTk.PhotoImage] = None

        self.items: List[PlaceholderItem] = []
        self.selected_item: Optional[PlaceholderItem] = None
        self.available_variables: List[str] = []
        self.sample_data_row: Dict[str, Any] = {}
        self.preview_sample_data: bool = False

        self.zoom_scale: float = 0.25  # Display scale relative to original resolution
        self.fit_to_screen: bool = True

        # Placement mode state
        self.pending_variable_to_place: Optional[str] = None

        # Interaction tracking state
        self.drag_mode: Optional[str] = None  # "move", "resize", "pan"
        self.active_handle: Optional[str] = None
        self.drag_start_canvas_x: float = 0
        self.drag_start_canvas_y: float = 0
        self.drag_start_item_state: Dict[str, float] = {}

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        # Control sub-bar for zoom and preview toggles
        self.toolbar = ttk.Frame(self)
        self.toolbar.pack(fill="x", side="top", padx=6, pady=4)

        ttk.Label(self.toolbar, text=f"Page {self.page_index + 1}", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 12))

        ttk.Button(self.toolbar, text="🔍 Zoom In (+)", width=12, command=self.zoom_in).pack(side="left", padx=2)
        ttk.Button(self.toolbar, text="🔍 Zoom Out (-)", width=12, command=self.zoom_out).pack(side="left", padx=2)
        ttk.Button(self.toolbar, text="📐 Fit View", width=10, command=self.fit_view).pack(side="left", padx=2)
        ttk.Button(self.toolbar, text="100%", width=6, command=lambda: self.set_zoom(1.0)).pack(side="left", padx=2)

        self.zoom_label = ttk.Label(self.toolbar, text="25%")
        self.zoom_label.pack(side="left", padx=8)

        # Student Row Navigator for live preview
        self.nav_frame = ttk.Frame(self.toolbar)
        self.nav_frame.pack(side="right", padx=(4, 8))

        self.prev_btn = ttk.Button(self.nav_frame, text="◀", width=3, command=self._prev_student)
        self.prev_btn.pack(side="left", padx=1)

        self.student_nav_lbl = ttk.Label(self.nav_frame, text="Student 1/1", font=("Segoe UI", 8, "bold"), foreground="#1e40af")
        self.student_nav_lbl.pack(side="left", padx=4)

        self.next_btn = ttk.Button(self.nav_frame, text="▶", width=3, command=self._next_student)
        self.next_btn.pack(side="left", padx=1)

        # Toggle Sample Data Preview
        self.preview_var = tk.BooleanVar(value=False)
        self.preview_cb = ttk.Checkbutton(
            self.toolbar,
            text="👁️ Live Preview",
            variable=self.preview_var,
            command=self._on_toggle_preview
        )
        self.preview_cb.pack(side="right", padx=6)

        # Placement indicator badge
        self.placement_lbl = ttk.Label(
            self.toolbar,
            text="",
            foreground="#d97706",
            font=("Segoe UI", 9, "bold")
        )
        self.placement_lbl.pack(side="right", padx=8)

        # Scrollable Canvas area
        canvas_container = ttk.Frame(self)
        canvas_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            canvas_container,
            bg="#2b2d30",
            highlightthickness=0
        )
        self.h_scroll = ttk.Scrollbar(canvas_container, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(canvas_container, orient="vertical", command=self.canvas.yview)

        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.h_scroll.pack(side="bottom", fill="x")
        self.v_scroll.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

    def _bind_events(self):
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Motion>", self._on_mouse_move)

        # Mouse wheel zoom
        self.canvas.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.canvas.bind("<MouseWheel>", self._on_wheel_scroll)

        # Middle mouse button panning
        self.canvas.bind("<ButtonPress-2>", self._on_pan_down)
        self.canvas.bind("<B2-Motion>", self._on_pan_drag)
        self.canvas.bind("<ButtonPress-3>", self._on_pan_down)
        self.canvas.bind("<B3-Motion>", self._on_pan_drag)

        # Keyboard Delete
        self.bind_all("<Delete>", self._on_delete_key)

    def set_template_image(self, image_path: str):
        """Loads and displays the template image."""
        p = Path(image_path)
        if not p.exists():
            return

        self.template_path = str(p.resolve())
        self.orig_image = Image.open(self.template_path).convert("RGB")

        if self.fit_to_screen:
            self.fit_view()
        else:
            self.refresh_canvas()

    def set_items(self, items: List[PlaceholderItem]):
        """Sets the active placeholders for this canvas page."""
        self.items = items
        self.refresh_canvas()

    def set_available_variables(self, vars_list: List[str]):
        self.available_variables = vars_list

    def set_sample_data(self, sample_row: Dict[str, Any]):
        self.sample_data_row = sample_row
        if self.preview_sample_data:
            self.refresh_canvas()

    def set_all_rows(self, rows: List[Dict[str, Any]]):
        self.all_rows = rows
        self.current_row_idx = 0
        if self.all_rows:
            self.sample_data_row = self.all_rows[0]
            self._update_nav_label()
        else:
            self.sample_data_row = {}
            self.student_nav_lbl.configure(text="No data")
        if self.preview_sample_data:
            self.refresh_canvas()

    def _update_nav_label(self):
        if not self.all_rows:
            self.student_nav_lbl.configure(text="No data")
            return
        total = len(self.all_rows)
        row = self.all_rows[self.current_row_idx]
        from generator import CertificateGenerator
        name = CertificateGenerator.match_column_value(row, "Name") or "Student"
        short_name = name[:12] + ".." if len(name) > 12 else name
        self.student_nav_lbl.configure(text=f"{self.current_row_idx + 1}/{total}: {short_name}")

    def _prev_student(self):
        if not self.all_rows:
            return
        self.current_row_idx = (self.current_row_idx - 1) % len(self.all_rows)
        self.sample_data_row = self.all_rows[self.current_row_idx]
        self._update_nav_label()
        if not self.preview_var.get():
            self.preview_var.set(True)
            self.preview_sample_data = True
        self.refresh_canvas()

    def _next_student(self):
        if not self.all_rows:
            return
        self.current_row_idx = (self.current_row_idx + 1) % len(self.all_rows)
        self.sample_data_row = self.all_rows[self.current_row_idx]
        self._update_nav_label()
        if not self.preview_var.get():
            self.preview_var.set(True)
            self.preview_sample_data = True
        self.refresh_canvas()

    def start_placement_mode(self, variable_name: str):
        """Prepares canvas for click-to-place of a variable."""
        self.pending_variable_to_place = variable_name
        self.canvas.configure(cursor="crosshair")
        self.placement_lbl.configure(text=f"Click on canvas to place: [{variable_name}]")

    def cancel_placement_mode(self):
        self.pending_variable_to_place = None
        self.canvas.configure(cursor="")
        self.placement_lbl.configure(text="")

    def _on_toggle_preview(self):
        self.preview_sample_data = self.preview_var.get()
        self.refresh_canvas()

    def fit_view(self):
        """Fits template image inside current visible canvas viewport."""
        if not self.orig_image:
            return
        cw = max(200, self.canvas.winfo_width())
        ch = max(200, self.canvas.winfo_height())
        iw, ih = self.orig_image.size

        # Fit with a 20px padding margin
        scale_w = (cw - 40) / float(iw)
        scale_h = (ch - 40) / float(ih)
        self.zoom_scale = max(0.05, min(scale_w, scale_h))
        self.fit_to_screen = True
        self.refresh_canvas()

    def zoom_in(self):
        self.set_zoom(self.zoom_scale * 1.25)

    def zoom_out(self):
        self.set_zoom(self.zoom_scale / 1.25)

    def set_zoom(self, new_scale: float):
        self.zoom_scale = max(0.05, min(2.5, new_scale))
        self.fit_to_screen = False
        self.refresh_canvas()

    def _on_ctrl_wheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def _on_wheel_scroll(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_pan_down(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _on_pan_drag(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_canvas_configure(self, event):
        if self.fit_to_screen and self.orig_image:
            self.fit_view()

    # -------------------------------------------------------------
    # Rendering on Canvas
    # -------------------------------------------------------------

    def refresh_canvas(self):
        """Redraws background template, all placeholder items, and selection handles."""
        self.canvas.delete("all")
        self.zoom_label.configure(text=f"{int(round(self.zoom_scale * 100))}%")

        if not self.orig_image:
            self.canvas.create_text(
                200, 150,
                text="No Template Uploaded.\nClick 'Upload Template' to load a page.",
                fill="#9ca3af",
                font=("Segoe UI", 12, "italic"),
                justify="center"
            )
            return

        iw, ih = self.orig_image.size
        sw = int(round(iw * self.zoom_scale))
        sh = int(round(ih * self.zoom_scale))

        # Margin offset to center image if smaller than viewport
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        offset_x = max(20, (cw - sw) // 2) if cw > sw else 20
        offset_y = max(20, (ch - sh) // 2) if ch > sh else 20
        self.offset_x = offset_x
        self.offset_y = offset_y

        # Resize template for display
        resized = self.orig_image.resize((sw, sh), Image.Resampling.BILINEAR)
        self.rendered_preview = ImageTk.PhotoImage(resized)

        # Draw template background
        self.canvas.create_image(
            offset_x, offset_y,
            anchor="nw",
            image=self.rendered_preview,
            tags="background"
        )

        # Set canvas scroll region
        self.canvas.config(scrollregion=(0, 0, offset_x * 2 + sw, offset_y * 2 + sh))

        # Draw all items on this page
        for item in self.items:
            self._draw_item(item)

        # Draw selection handles if an item is selected
        if self.selected_item and self.selected_item in self.items:
            self._draw_selection_handles(self.selected_item)

    def _native_to_canvas(self, x: float, y: float) -> Tuple[float, float]:
        cx = self.offset_x + x * self.zoom_scale
        cy = self.offset_y + y * self.zoom_scale
        return cx, cy

    def _canvas_to_native(self, cx: float, cy: float) -> Tuple[float, float]:
        nx = (cx - self.offset_x) / self.zoom_scale
        ny = (cy - self.offset_y) / self.zoom_scale
        return nx, ny

    def _draw_item(self, item: PlaceholderItem):
        x1, y1 = self._native_to_canvas(item.x, item.y)
        x2, y2 = self._native_to_canvas(item.x + item.width, item.y + item.height)

        is_sel = (item == self.selected_item)
        border_color = "#f59e0b" if is_sel else ("#2563eb" if not item.is_signature else "#7c3aed")
        fill_color = ""

        # Draw rectangle
        rect_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline=border_color,
            width=2 if is_sel else 1,
            fill=fill_color,
            dash=(4, 2) if not is_sel else (),
            tags=("placeholder", item.id)
        )

        # Display text content
        if item.is_signature:
            display_str = "✒️ [Signature Stamp]"
            font_size = max(9, int(13 * self.zoom_scale * 2.5))
            text_color = "#6d28d9"
            self.canvas.create_text(
                (x1 + x2) / 2, (y1 + y2) / 2,
                text=display_str,
                font=("Segoe UI", font_size, "bold"),
                fill=text_color,
                tags=("placeholder_text", item.id)
            )
        else:
            if self.preview_sample_data and self.sample_data_row:
                # Show real sample value
                from generator import CertificateGenerator
                val = CertificateGenerator.match_column_value(self.sample_data_row, item.name)
                display_str = f"{item.prefix}{val}{item.suffix}" if val else f"[{item.name}]"
            else:
                display_str = f"[{item.name}]"

            font_size = max(8, int(item.font_size * self.zoom_scale))
            align = item.alignment

            if align == "center":
                anchor = "center"
                tx = (x1 + x2) / 2
            elif align == "right":
                anchor = "e"
                tx = x2 - 4
            else:
                anchor = "w"
                tx = x1 + 4

            ty = (y1 + y2) / 2
            self.canvas.create_text(
                tx, ty,
                text=display_str,
                anchor=anchor,
                font=("Segoe UI", font_size, "bold"),
                fill=item.font_color,
                tags=("placeholder_text", item.id)
            )

        # Small top badge
        badge_y = max(0, y1 - 14)
        badge_bg = self.canvas.create_rectangle(
            x1, badge_y, x1 + min(len(item.name) * 7 + 10, 160), y1,
            fill=border_color,
            outline="",
            tags=("badge", item.id)
        )
        self.canvas.create_text(
            x1 + 4, badge_y + 7,
            text=item.name[:20],
            anchor="w",
            fill="#ffffff",
            font=("Segoe UI", 7, "bold"),
            tags=("badge_text", item.id)
        )

    def _draw_selection_handles(self, item: PlaceholderItem):
        x1, y1 = self._native_to_canvas(item.x, item.y)
        x2, y2 = self._native_to_canvas(item.x + item.width, item.y + item.height)
        xc = (x1 + x2) / 2
        yc = (y1 + y2) / 2

        coords = {
            "nw": (x1, y1),
            "n": (xc, y1),
            "ne": (x2, y1),
            "e": (x2, yc),
            "se": (x2, y2),
            "s": (xc, y2),
            "sw": (x1, y2),
            "w": (x1, yc),
        }

        for pos, (hx, hy) in coords.items():
            h_id = self.canvas.create_rectangle(
                hx - HANDLE_SIZE // 2,
                hy - HANDLE_SIZE // 2,
                hx + HANDLE_SIZE // 2,
                hy + HANDLE_SIZE // 2,
                fill="#ffffff",
                outline="#f59e0b",
                width=2,
                tags=("handle", pos, item.id)
            )

    # -------------------------------------------------------------
    # Interaction Handling
    # -------------------------------------------------------------

    def _get_item_under_mouse(self, cx: float, cy: float) -> Optional[PlaceholderItem]:
        for item in reversed(self.items):
            x1, y1 = self._native_to_canvas(item.x, item.y)
            x2, y2 = self._native_to_canvas(item.x + item.width, item.y + item.height)
            if x1 <= cx <= x2 and y1 <= cy <= y2:
                return item
        return None

    def _get_handle_under_mouse(self, cx: float, cy: float) -> Optional[str]:
        if not self.selected_item:
            return None
        item = self.selected_item
        x1, y1 = self._native_to_canvas(item.x, item.y)
        x2, y2 = self._native_to_canvas(item.x + item.width, item.y + item.height)
        xc = (x1 + x2) / 2
        yc = (y1 + y2) / 2

        coords = {
            "nw": (x1, y1), "n": (xc, y1), "ne": (x2, y1), "e": (x2, yc),
            "se": (x2, y2), "s": (xc, y2), "sw": (x1, y2), "w": (x1, yc),
        }
        for pos, (hx, hy) in coords.items():
            if abs(cx - hx) <= HANDLE_SIZE and abs(cy - hy) <= HANDLE_SIZE:
                return pos
        return None

    def _on_mouse_down(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        # 1. Placement Mode Check
        if self.pending_variable_to_place:
            nx, ny = self._canvas_to_native(cx, cy)
            is_sig = ("sig" in self.pending_variable_to_place.lower())
            new_item = PlaceholderItem(
                name=self.pending_variable_to_place,
                page_index=self.page_index,
                x=max(0, nx - 150),
                y=max(0, ny - 35),
                width=350 if is_sig else 450,
                height=130 if is_sig else 75,
                is_signature=is_sig,
                font_family="PTSerif-Bold" if self.page_index == 0 else "Poppins-Bold",
                font_size=50,
                alignment="center" if self.page_index == 0 else "left"
            )
            self.items.append(new_item)
            self.selected_item = new_item
            self.cancel_placement_mode()
            self.refresh_canvas()
            if self.on_items_changed:
                self.on_items_changed()
            if self.on_selection_changed:
                self.on_selection_changed(new_item)
            return

        # 2. Check resize handles of selected item
        handle = self._get_handle_under_mouse(cx, cy)
        if handle and self.selected_item:
            self.drag_mode = "resize"
            self.active_handle = handle
            self.drag_start_canvas_x = cx
            self.drag_start_canvas_y = cy
            self.drag_start_item_state = {
                "x": self.selected_item.x,
                "y": self.selected_item.y,
                "width": self.selected_item.width,
                "height": self.selected_item.height
            }
            return

        # 3. Check item hit
        hit_item = self._get_item_under_mouse(cx, cy)
        if hit_item:
            self.selected_item = hit_item
            self.drag_mode = "move"
            self.drag_start_canvas_x = cx
            self.drag_start_canvas_y = cy
            self.drag_start_item_state = {
                "x": hit_item.x,
                "y": hit_item.y,
                "width": hit_item.width,
                "height": hit_item.height
            }
            self.refresh_canvas()
            if self.on_selection_changed:
                self.on_selection_changed(hit_item)
        else:
            # Clicked outside: deselect
            if self.selected_item:
                self.selected_item = None
                self.refresh_canvas()
                if self.on_selection_changed:
                    self.on_selection_changed(None)

    def _on_mouse_drag(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if not self.selected_item or not self.drag_mode:
            return

        delta_canvas_x = cx - self.drag_start_canvas_x
        delta_canvas_y = cy - self.drag_start_canvas_y
        delta_native_x = delta_canvas_x / self.zoom_scale
        delta_native_y = delta_canvas_y / self.zoom_scale

        orig = self.drag_start_item_state

        if self.drag_mode == "move":
            new_x = max(0, orig["x"] + delta_native_x)
            new_y = max(0, orig["y"] + delta_native_y)
            if self.orig_image:
                new_x = min(self.orig_image.width - orig["width"], new_x)
                new_y = min(self.orig_image.height - orig["height"], new_y)
            self.selected_item.x = round(new_x, 1)
            self.selected_item.y = round(new_y, 1)
            self.refresh_canvas()

        elif self.drag_mode == "resize" and self.active_handle:
            h = self.active_handle
            nx = orig["x"]
            ny = orig["y"]
            nw = orig["width"]
            nh = orig["height"]

            if "e" in h:
                nw = max(30, orig["width"] + delta_native_x)
            if "s" in h:
                nh = max(20, orig["height"] + delta_native_y)
            if "w" in h:
                effective_dx = min(orig["width"] - 30, delta_native_x)
                nx = orig["x"] + effective_dx
                nw = orig["width"] - effective_dx
            if "n" in h:
                effective_dy = min(orig["height"] - 20, delta_native_y)
                ny = orig["y"] + effective_dy
                nh = orig["height"] - effective_dy

            self.selected_item.x = round(nx, 1)
            self.selected_item.y = round(ny, 1)
            self.selected_item.width = round(nw, 1)
            self.selected_item.height = round(nh, 1)
            self.refresh_canvas()

    def _on_mouse_up(self, event):
        if self.drag_mode:
            self.drag_mode = None
            self.active_handle = None
            if self.on_items_changed:
                self.on_items_changed()

    def _on_mouse_move(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)

        if self.pending_variable_to_place:
            return

        handle = self._get_handle_under_mouse(cx, cy)
        if handle:
            self.canvas.configure(cursor=CURSOR_MAP.get(handle, "arrow"))
        elif self._get_item_under_mouse(cx, cy):
            self.canvas.configure(cursor="fleur")
        else:
            self.canvas.configure(cursor="")

    def _on_double_click(self, event):
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        hit_item = self._get_item_under_mouse(cx, cy)
        if hit_item:
            self.selected_item = hit_item
            self.open_item_inspector(hit_item)

    def open_item_inspector(self, item: PlaceholderItem):
        """Opens property dialog for the item."""
        dialog = ItemPropertiesDialog(
            self.winfo_toplevel(),
            item=item,
            available_variables=self.available_variables,
            on_update=self._on_inspector_update,
            on_delete=self._on_inspector_delete
        )

    def _on_inspector_update(self, item: PlaceholderItem):
        self.refresh_canvas()
        if self.on_items_changed:
            self.on_items_changed()
        if self.on_selection_changed:
            self.on_selection_changed(item)

    def _on_inspector_delete(self, item: PlaceholderItem):
        if item in self.items:
            self.items.remove(item)
            if self.selected_item == item:
                self.selected_item = None
            self.refresh_canvas()
            if self.on_items_changed:
                self.on_items_changed()
            if self.on_selection_changed:
                self.on_selection_changed(None)

    def _on_delete_key(self, event):
        if self.selected_item and self.selected_item in self.items:
            self._on_inspector_delete(self.selected_item)
