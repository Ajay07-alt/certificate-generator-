"""
Document generation engine for Visual Bulk Certificate Generator.
Handles smart Excel ingestion, high-DPI Pillow rendering, font management,
transparent signature overlays, and 2-page PDF compilation.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from models import PlaceholderItem, ProjectConfig

TAMIL_REGEX = re.compile(r'[\u0B80-\u0BFF]')

def sanitize_filename(name: str) -> str:
    """Remove illegal filesystem characters from filename."""
    name = str(name).strip()
    name = re.sub(r'[\\/*?:"<>|\t\n\r]', '_', name)
    name = re.sub(r'_+', '_', name).strip('._ ')
    return name or "certificate"


class ExcelDataLoader:
    """
    Intelligently loads Excel data, handling both clean tabular sheets
    and academic attendance sheets with metadata headers across multiple sheets.
    """

    @staticmethod
    def get_sheet_names(file_path: str) -> List[str]:
        """Returns all available sheet/page names in the Excel file."""
        p = Path(file_path)
        if not p.exists():
            return []
        if p.suffix.lower() in [".csv", ".tsv"]:
            return ["Default"]
        try:
            xl = pd.ExcelFile(file_path)
            # Return sheet names, putting non-empty ones first
            valid_sheets = []
            for s in xl.sheet_names:
                valid_sheets.append(s)
            return valid_sheets or ["Sheet1"]
        except Exception:
            return ["Sheet1"]

    @staticmethod
    def load(file_path: str, sheet_name: Optional[str] = None) -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
        """
        Loads an Excel file (optionally for a specific sheet) and returns (cleaned_dataframe, column_names, metadata_dict).
        """
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        # Read raw sheet to find table start
        try:
            if p.suffix.lower() in [".csv", ".tsv"]:
                raw_df = pd.read_csv(file_path, header=None)
                current_sheet = "Default"
            else:
                if not sheet_name:
                    available = ExcelDataLoader.get_sheet_names(file_path)
                    sheet_name = available[0] if available else 0
                raw_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                current_sheet = str(sheet_name)
        except Exception as e:
            raise ValueError(f"Failed to read sheet '{sheet_name}' in {p.name}: {e}")

        metadata: Dict[str, str] = {"Sheet": current_sheet}
        header_row_idx = -1

        # Scan first 25 rows to detect metadata and the real table header row
        for idx, row in raw_df.iterrows():
            if idx > 25:
                break
            vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip()]
            line_str = " ".join(vals)

            # Metadata extraction heuristics
            if "DEPARTMENT OF" in line_str.upper() or "DEPT :" in line_str.upper() or "DEPT:" in line_str.upper():
                dept_val = line_str
                if ":" in line_str:
                    dept_val = line_str.split(":", 1)[-1].strip()
                elif "DEPARTMENT OF" in line_str.upper():
                    dept_val = re.split(r'DEPARTMENT OF', line_str, flags=re.IGNORECASE)[-1].strip()
                metadata["Department"] = dept_val

            if "DATE:" in line_str.upper() or "DATE :" in line_str.upper() or "PERIOD" in line_str.upper():
                date_part = line_str
                for prefix in ["DATE:", "DATE :", "Date:", "PERIOD FROM", "PERIOD"]:
                    date_part = date_part.replace(prefix, "").strip()
                metadata["Dates"] = date_part

                if " to " in date_part.lower():
                    parts = re.split(r'\s+to\s+', date_part, flags=re.IGNORECASE)
                    metadata["From Date"] = parts[0].strip()
                    metadata["To Date"] = parts[1].strip()

            if "ACADEMIC YEAR" in line_str.upper():
                metadata["Academic Year"] = line_str

            # Check if this row is the table header
            lower_vals = [v.lower() for v in vals]
            has_student = any("student" in v or "name" in v for v in lower_vals)
            has_reg = any("register" in v or "reg" in v or "roll" in v for v in lower_vals)
            has_sno = any("s.no" in v or "sl.no" in v or "sno" in v for v in lower_vals)

            if (has_student and has_reg) or (has_reg and has_sno) or (has_student and has_sno):
                header_row_idx = idx
                break

        if header_row_idx >= 0:
            if p.suffix.lower() in [".csv", ".tsv"]:
                df = pd.read_csv(file_path, skiprows=header_row_idx)
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, skiprows=header_row_idx)
        else:
            # Fallback to standard 0-header
            if p.suffix.lower() in [".csv", ".tsv"]:
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name)

        # Clean column names
        cleaned_cols = []
        for i, col in enumerate(df.columns):
            c_str = str(col).strip()
            if not c_str or "unnamed" in c_str.lower():
                c_str = f"Column_{i+1}"
            cleaned_cols.append(c_str)
        df.columns = cleaned_cols

        # Filter out trailing empty rows or footer notes
        df = df.dropna(how="all").reset_index(drop=True)
        # Drop rows where register number/name is missing if such column exists
        reg_col = next((c for c in df.columns if any(k in c.lower() for k in ["register", "reg", "roll"])), None)
        name_col = next((c for c in df.columns if "name" in c.lower()), None)
        if reg_col:
            df = df[df[reg_col].notna() & (df[reg_col].astype(str).str.strip() != "")]
        elif name_col:
            df = df[df[name_col].notna() & (df[name_col].astype(str).str.strip() != "")]

        df = df.reset_index(drop=True)

        # Detect attendance columns (e.g. DAY 1, DAY 2, DAY 3...)
        day_cols = [c for c in df.columns if re.match(r'^(day\s*\d+|d\d+)$', c.strip(), re.IGNORECASE)]
        if day_cols and "Student Attendance" not in df.columns and "Attendance %" not in df.columns:
            # Compute attendance percentage from 'P' presence
            attend_vals = []
            for _, row in df.iterrows():
                total_days = len(day_cols)
                present_days = sum(1 for c in day_cols if str(row[c]).strip().upper() in ['P', '1', 'PRESENT'])
                pct = int(round((present_days / total_days) * 100)) if total_days > 0 else 100
                attend_vals.append(f"{pct}%")
            df["Student Attendance"] = attend_vals
            df["Attendance %"] = attend_vals

        # Add computed fields if absent
        if "Certificate No" not in df.columns:
            df["Certificate No"] = [f"PEC/ROB/2026/{i+1:03d}" for i in range(len(df))]
        if "Date of Issue" not in df.columns:
            today_str = datetime.now().strftime("%d.%m.%Y")
            df["Date of Issue"] = today_str
        if "Grade Obtained" not in df.columns:
            df["Grade Obtained"] = "A+"
        if "Mini Project Done" not in df.columns:
            df["Mini Project Done"] = "Obstacle Avoiding Mobile Robot & Automation"

        # Apply metadata fallbacks
        if "Department" in metadata and "Department" not in df.columns:
            df["Department"] = metadata["Department"]
        if "From Date" in metadata and "From Date" not in df.columns:
            df["From Date"] = metadata["From Date"]
        if "To Date" in metadata and "To Date" not in df.columns:
            df["To Date"] = metadata["To Date"]

        # Clean all cells to strip unwanted decimal points (.0) from register numbers, certificate numbers, etc.
        df = df.map(clean_display_value)

        # Detect percentage / attendance columns and ensure proper % formatting (e.g. 1 -> 100%)
        for col in df.columns:
            if any(k in str(col).lower() for k in ["attendance", "percentage", "percent", "%"]):
                df[col] = df[col].apply(format_percentage_value)

        return df, list(df.columns), metadata


def clean_display_value(val: Any) -> str:
    """
    Sanitizes values to eliminate unwanted decimal points (.0) from
    register numbers, certificate numbers, roll numbers, and whole numbers.
    """
    if val is None or pd.isna(val):
        return ""
    
    # If float or integer
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        elif isinstance(val, int):
            return str(val)
        return f"{val:g}"
    
    s = str(val).strip()
    
    # Check if string representation is an integer float like "111424205004.0" or "142.0"
    if re.match(r'^-?\d+\.0+$', s):
        return s.split('.')[0]
        
    return s


def format_percentage_value(val: Any) -> str:
    """
    Converts raw percentage representations into clean percentage strings.
    E.g. 1 -> '100%', 1.0 -> '100%', 0.85 -> '85%', 100 -> '100%', '95%' -> '95%'.
    """
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if not s:
        return ""
    if "%" in s:
        return s
    try:
        num = float(s)
        if 0.0 < num <= 1.0:
            return f"{int(round(num * 100))}%"
        elif 1.0 < num <= 100.0:
            if num.is_integer():
                return f"{int(num)}%"
            return f"{num:g}%"
        elif num == 0.0:
            return "0%"
    except ValueError:
        pass
    return s


def split_into_two_lines(text: str) -> str:
    """
    Splits a long text string into 2 balanced lines at word boundaries.
    E.g. 'PLC-BASED SMART MANUFACTURING CONVEYOR' -> 'PLC-BASED SMART\nMANUFACTURING CONVEYOR'.
    """
    if not text or "\n" in text:
        return text
    words = text.split()
    if len(words) <= 1:
        return text
    best_diff = float("inf")
    best_split = None
    for i in range(1, len(words)):
        l1 = " ".join(words[:i])
        l2 = " ".join(words[i:])
        diff = abs(len(l1) - len(l2))
        if diff < best_diff:
            best_diff = diff
            best_split = f"{l1}\n{l2}"
    return best_split or text


class FontManager:
    """Manages and caches TrueType fonts with Unicode/Tamil fallback support."""

    def __init__(self, font_dirs: Optional[List[Path]] = None):
        self.font_dirs = font_dirs or []
        # Add default app fonts directory
        default_dir = Path(__file__).resolve().parent / "assets" / "fonts"
        if default_dir.exists() and default_dir not in self.font_dirs:
            self.font_dirs.append(default_dir)
        self._font_cache: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

    def get_font_file(self, font_family: str, is_tamil: bool = False) -> Optional[Path]:
        """Finds TTF font file path for the given family."""
        if is_tamil:
            font_family = "NotoSansTamil-Bold" if "Bold" in font_family else "NotoSansTamil-Regular"

        # Direct search
        for d in self.font_dirs:
            p = d / f"{font_family}.ttf"
            if p.exists():
                return p
            # Case-insensitive search
            for f in d.glob("*.ttf"):
                if f.stem.lower() == font_family.lower():
                    return f

        # Fallback to system fonts or default
        for d in self.font_dirs:
            for f in d.glob("*.ttf"):
                return f
        return None

    def get_font(self, font_family: str, font_size: int, is_tamil: bool = False) -> ImageFont.FreeTypeFont:
        key = (font_family, font_size, is_tamil)
        if key in self._font_cache:
            return self._font_cache[key]

        font_path = self.get_font_file(font_family, is_tamil)
        if font_path and font_path.exists():
            try:
                font = ImageFont.truetype(str(font_path), size=font_size)
                self._font_cache[key] = font
                return font
            except Exception:
                pass

        # Fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", size=font_size)
        except Exception:
            font = ImageFont.load_default()
        self._font_cache[key] = font
        return font


class CertificateGenerator:
    """
    Renders dynamic certificates on full-resolution template images and
    exports 2-page PDFs with transparent signature stamping and auto-shrinking text.
    """

    def __init__(self, config: ProjectConfig):
        self.config = config
        self.font_manager = FontManager()

    @staticmethod
    def match_column_value(row_data: Dict[str, Any], placeholder_name: str) -> str:
        """
        Matches a placeholder name to row values using exact match or smart aliases,
        stripping unwanted decimals (.0) and formatting percentages (e.g. 1 -> 100%).
        """
        p_clean = placeholder_name.lower().replace("_", " ").replace(".", "").strip()
        is_percent_field = any(k in p_clean for k in ["attendance", "percentage", "percent", "%"])

        def post_process(val: Any) -> str:
            cleaned = clean_display_value(val)
            if is_percent_field:
                return format_percentage_value(cleaned)
            return cleaned

        # Exact match
        if placeholder_name in row_data:
            return post_process(row_data[placeholder_name])

        # Alias dictionary
        aliases = {
            "name": ["name of the student", "student name", "student_name", "candidate name", "name"],
            "register no": ["register number", "register no", "reg no", "reg. no", "regno", "roll no"],
            "department": ["dept", "department", "branch", "dept:"],
            "from date": ["from date", "from_date", "start date", "date from"],
            "to date": ["to date", "to_date", "end date", "date to"],
            "certificate no": ["certificate no", "certificate number", "cert no", "cert_no", "certificate_no"],
            "date of issue": ["date of issue", "issue date", "date_of_issue", "issue_date"],
            "grade obtained": ["grade", "grade obtained", "grade_obtained"],
            "student attendance": ["student attendance", "attendance", "attendance %", "attendance percentage", "percentage", "percent"],
            "mini project done": ["mini project done", "project name", "project", "mini project"],
        }

        # Check alias keys
        target_keys = aliases.get(p_clean, [p_clean])
        for col_name, val in row_data.items():
            c_clean = str(col_name).lower().replace("_", " ").replace(".", "").strip()
            if c_clean in target_keys or any(t in c_clean for t in target_keys):
                return post_process(val)

        # Fuzzy partial match
        for col_name, val in row_data.items():
            c_clean = str(col_name).lower()
            if p_clean in c_clean or c_clean in p_clean:
                return post_process(val)

        return ""

    def _render_text(self, draw: ImageDraw.ImageDraw, item: PlaceholderItem, text: str):
        """Draws text within the bounding box with auto-shrink, multiline wrapping, and proper alignment."""
        if not text:
            return

        # Check if text should be split into 2 lines
        should_split = (
            "\n" in text
            or getattr(item, "multi_line", False)
            or getattr(item, "max_lines", 1) >= 2
            or (any(k in item.name.lower() for k in ["project", "mini project", "title"]) and len(text.split()) >= 3)
        )
        if should_split and "\n" not in text:
            text = split_into_two_lines(text)

        is_multiline = "\n" in text
        is_tamil = bool(TAMIL_REGEX.search(text))
        font_size = item.font_size
        font = self.font_manager.get_font(item.font_family, font_size, is_tamil=is_tamil)
        spacing = max(4, int(font_size * 0.2))

        # Auto-shrink if text overflows box width or height
        if item.auto_shrink:
            min_size = max(12, int(item.font_size * 0.35))
            while font_size > min_size:
                if is_multiline:
                    bbox = draw.multiline_textbbox((0, 0), text, font=font, align=item.alignment, spacing=spacing)
                else:
                    bbox = draw.textbbox((0, 0), text, font=font)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                if text_w <= item.width and text_h <= item.height:
                    break
                font_size -= 2
                font = self.font_manager.get_font(item.font_family, font_size, is_tamil=is_tamil)
                spacing = max(4, int(font_size * 0.2))

        if is_multiline:
            bbox = draw.multiline_textbbox((0, 0), text, font=font, align=item.alignment, spacing=spacing)
        else:
            bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Calculate X based on alignment
        if item.alignment == "center":
            draw_x = item.x + (item.width - text_w) / 2.0 - bbox[0]
        elif item.alignment == "right":
            draw_x = item.x + item.width - text_w - bbox[0]
        else:  # left
            draw_x = item.x - bbox[0]

        # Vertically center inside the bounding box
        draw_y = item.y + (item.height - text_h) / 2.0 - bbox[1]

        if is_multiline:
            draw.multiline_text((draw_x, draw_y), text, font=font, fill=item.font_color, align=item.alignment, spacing=spacing)
        else:
            draw.text((draw_x, draw_y), text, font=font, fill=item.font_color)

    def _overlay_signature(self, base_image: Image.Image, item: PlaceholderItem, default_sig_path: str):
        """Overlays the signature image onto the base image with transparency support."""
        sig_path = item.image_path or default_sig_path
        if not sig_path or not Path(sig_path).exists():
            return

        try:
            with Image.open(sig_path) as sig_img:
                sig_img = sig_img.convert("RGBA")
                target_w = max(10, int(item.width))
                target_h = max(10, int(item.height))
                resized_sig = sig_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

                # Paste onto base image using alpha mask
                dest_x = int(item.x)
                dest_y = int(item.y)
                base_image.paste(resized_sig, (dest_x, dest_y), mask=resized_sig)
        except Exception as e:
            print(f"Warning: Failed to stamp signature: {e}")

    def render_page(self, template_img: Image.Image, page_index: int, row_data: Dict[str, Any]) -> Image.Image:
        """Renders one page (0: Front, 1: Back) with all placed items."""
        page_copy = template_img.copy()
        draw = ImageDraw.Draw(page_copy)

        page_items = [it for it in self.config.items if it.page_index == page_index]

        # Draw signatures first
        for item in page_items:
            if item.is_signature:
                self._overlay_signature(page_copy, item, self.config.signature_path)

        # Draw text items on top
        for item in page_items:
            if not item.is_signature:
                text = self.match_column_value(row_data, item.name)
                full_text = f"{item.prefix}{text}{item.suffix}"
                self._render_text(draw, item, full_text)

        return page_copy

    def generate_all(
        self,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> List[Path]:
        """
        Executes the batch generation loop for all rows in the Excel data.
        Supports generating the active sheet or all sheets in the workbook.
        """
        # Validate required templates based on page_count
        page_count = getattr(self.config, "page_count", 1)
        if page_count < 1:
            page_count = 1

        # Resolve template paths
        tpl_paths: List[str] = []
        if getattr(self.config, "template_paths", None) and len(self.config.template_paths) >= page_count:
            tpl_paths = self.config.template_paths[:page_count]
        else:
            tpl_paths = [self.config.front_template_path]
            if page_count >= 2:
                tpl_paths.append(self.config.back_template_path)

        for p_idx in range(page_count):
            tpl = tpl_paths[p_idx] if p_idx < len(tpl_paths) else ""
            if not tpl or not Path(tpl).exists():
                p_label = "Front Page (Page 1)" if p_idx == 0 else f"Page {p_idx + 1}"
                raise FileNotFoundError(f"{p_label} template image not found: '{tpl}'")

        if not Path(self.config.excel_data_path).exists():
            raise FileNotFoundError(f"Excel data file not found: {self.config.excel_data_path}")

        base_out_dir = Path(self.config.output_dir or "output_certificates")
        base_out_dir.mkdir(parents=True, exist_ok=True)

        # Determine sheets to generate
        available_sheets = ExcelDataLoader.get_sheet_names(self.config.excel_data_path)
        if self.config.generate_all_sheets:
            sheets_to_process = available_sheets
        else:
            if self.config.selected_sheet and self.config.selected_sheet in available_sheets:
                target_sheet = self.config.selected_sheet
            else:
                target_sheet = available_sheets[0] if available_sheets else None
            sheets_to_process = [target_sheet] if target_sheet else []

        # Pre-count total rows across all sheets for accurate progress reporting
        sheet_data_map: Dict[str, pd.DataFrame] = {}
        total_rows = 0
        for s in sheets_to_process:
            try:
                df, _, _ = ExcelDataLoader.load(self.config.excel_data_path, sheet_name=s)
                if len(df) > 0:
                    sheet_data_map[s] = df
                    total_rows += len(df)
            except Exception as e:
                print(f"Skipping empty or invalid sheet '{s}': {e}")

        if total_rows == 0:
            raise ValueError("No valid student rows found in selected sheet(s).")

        # Load only the active page templates into memory
        page_templates = [Image.open(tpl_paths[i]).convert("RGB") for i in range(page_count)]

        generated_pdfs: List[Path] = []
        overall_idx = 0

        for sheet_name, df in sheet_data_map.items():
            # If multiple sheets, organize into sheet-specific subfolders
            if len(sheet_data_map) > 1:
                sheet_out_dir = base_out_dir / sanitize_filename(sheet_name)
                sheet_out_dir.mkdir(parents=True, exist_ok=True)
            else:
                sheet_out_dir = base_out_dir

            for _, row in df.iterrows():
                if cancel_check and cancel_check():
                    return generated_pdfs

                overall_idx += 1
                row_dict = row.to_dict()

                # Render only the active pages (1 page or 2 pages)
                rendered_pages: List[Image.Image] = []
                for p_idx in range(page_count):
                    p_img = self.render_page(page_templates[p_idx], page_index=p_idx, row_data=row_dict)
                    rendered_pages.append(p_img.convert("RGB"))

                # Determine dynamic filename
                reg_val = self.match_column_value(row_dict, "Register No") or f"REG{overall_idx:03d}"
                name_val = self.match_column_value(row_dict, "Name") or f"Student_{overall_idx}"
                pdf_filename = f"{sanitize_filename(reg_val)}_{sanitize_filename(name_val)}.pdf"
                pdf_path = sheet_out_dir / pdf_filename

                # Save as single-page PDF (count=1) or multi-page PDF (count>=2)
                if len(rendered_pages) == 1:
                    rendered_pages[0].save(
                        str(pdf_path),
                        resolution=300.0,
                        quality=95
                    )
                else:
                    rendered_pages[0].save(
                        str(pdf_path),
                        save_all=True,
                        append_images=rendered_pages[1:],
                        resolution=300.0,
                        quality=95
                    )

                generated_pdfs.append(pdf_path)

                if progress_callback:
                    label = f"[{sheet_name}] {pdf_filename}" if len(sheet_data_map) > 1 else pdf_filename
                    progress_callback(overall_idx, total_rows, label)

        return generated_pdfs
