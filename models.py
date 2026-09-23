"""
Data models for the Visual Bulk Certificate Generator.
Defines placeholder items, styles, coordinates, and project configuration.
"""

from dataclasses import dataclass, field, asdict
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

@dataclass
class PlaceholderItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Variable"
    page_index: int = 0  # 0: Front Page, 1: Back Page
    x: float = 100.0     # Native full-resolution image X
    y: float = 100.0     # Native full-resolution image Y
    width: float = 400.0 # Native full-resolution bounding box width
    height: float = 80.0 # Native full-resolution bounding box height
    font_family: str = "PTSerif-Bold"
    font_size: int = 50
    font_color: str = "#112354"
    alignment: str = "center"  # "left", "center", "right"
    is_signature: bool = False
    image_path: Optional[str] = None
    auto_shrink: bool = True
    prefix: str = ""
    suffix: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlaceholderItem":
        # Filter keys to match dataclass fields
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class ProjectConfig:
    page_count: int = 1  # 1: Front Only, 2: Front & Back
    template_paths: List[str] = field(default_factory=list)
    front_template_path: str = ""
    back_template_path: str = ""
    excel_data_path: str = ""
    signature_path: str = ""
    output_dir: str = ""
    naming_pattern: str = "{Register No}_{Name}.pdf"
    selected_sheet: str = ""
    generate_all_sheets: bool = False
    items: List[PlaceholderItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_count": self.page_count,
            "template_paths": self.template_paths,
            "front_template_path": self.front_template_path,
            "back_template_path": self.back_template_path,
            "excel_data_path": self.excel_data_path,
            "signature_path": self.signature_path,
            "output_dir": self.output_dir,
            "naming_pattern": self.naming_pattern,
            "selected_sheet": self.selected_sheet,
            "generate_all_sheets": self.generate_all_sheets,
            "items": [item.to_dict() for item in self.items]
        }

    def save_to_json(self, file_path: str) -> None:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load_from_json(cls, file_path: str) -> "ProjectConfig":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = [PlaceholderItem.from_dict(item_data) for item_data in data.get("items", [])]
        
        # Determine page count with backwards compatibility
        page_count = data.get("page_count")
        if page_count is None:
            if data.get("back_template_path") or any(it.page_index >= 1 for it in items):
                page_count = 2
            else:
                page_count = 1

        tpl_paths = data.get("template_paths", [])
        if not tpl_paths:
            f = data.get("front_template_path", "")
            b = data.get("back_template_path", "")
            tpl_paths = [f] if f else []
            if b:
                tpl_paths.append(b)

        return cls(
            page_count=page_count,
            template_paths=tpl_paths,
            front_template_path=data.get("front_template_path", ""),
            back_template_path=data.get("back_template_path", ""),
            excel_data_path=data.get("excel_data_path", ""),
            signature_path=data.get("signature_path", ""),
            output_dir=data.get("output_dir", ""),
            naming_pattern=data.get("naming_pattern", "{Register No}_{Name}.pdf"),
            selected_sheet=data.get("selected_sheet", ""),
            generate_all_sheets=data.get("generate_all_sheets", False),
            items=items
        )
