/**
 * Interactive Client-side Application for Visual Bulk Certificate Generator.
 * Manages canvas rendering, drag-and-drop, resize handles, uploads, preview, and generation.
 */

// State
const state = {
  pageCount: 1,
  activePage: 0, // 0: Front, 1: Back
  zoom: 1.0,
  nativeDimensions: {
    0: { width: 2000, height: 1414 },
    1: { width: 2000, height: 1414 }
  },
  templateUrls: {
    0: null,
    1: null
  },
  excel: {
    sheets: [],
    activeSheet: "",
    totalStudents: 0,
    sampleRows: [],
    columns: []
  },
  studentIndex: 0,
  items: [],
  selectedItemId: null,
  isPreviewMode: false
};

// DOM Elements
const pageCountSelect = document.getElementById("pageCountSelect");
const sheetSelect = document.getElementById("sheetSelect");
const prevStudentBtn = document.getElementById("prevStudentBtn");
const nextStudentBtn = document.getElementById("nextStudentBtn");
const studentNavLabel = document.getElementById("studentNavLabel");
const autoPlaceBtn = document.getElementById("autoPlaceBtn");
const previewToggleBtn = document.getElementById("previewToggleBtn");
const generateBtn = document.getElementById("generateBtn");

const frontUploadCard = document.getElementById("frontUploadCard");
const backUploadCard = document.getElementById("backUploadCard");
const excelUploadCard = document.getElementById("excelUploadCard");
const sigUploadCard = document.getElementById("sigUploadCard");

const frontFileInput = document.getElementById("frontFileInput");
const backFileInput = document.getElementById("backFileInput");
const excelFileInput = document.getElementById("excelFileInput");
const sigFileInput = document.getElementById("sigFileInput");

const tabFrontBtn = document.getElementById("tabFrontBtn");
const tabBackBtn = document.getElementById("tabBackBtn");
const fieldListContainer = document.getElementById("fieldListContainer");
const addFieldBtn = document.getElementById("addFieldBtn");

const canvasStage = document.getElementById("canvasStage");
const canvasBgImage = document.getElementById("canvasBgImage");
const placeholderLayer = document.getElementById("placeholderLayer");
const canvasPageIndicator = document.getElementById("canvasPageIndicator");
const canvasDimLabel = document.getElementById("canvasDimLabel");
const stageWrapper = document.getElementById("stageWrapper");
const previewContainer = document.getElementById("previewContainer");
const previewImg = document.getElementById("previewImg");

const zoomInBtn = document.getElementById("zoomInBtn");
const zoomOutBtn = document.getElementById("zoomOutBtn");
const zoomResetBtn = document.getElementById("zoomResetBtn");
const zoomLevelLabel = document.getElementById("zoomLevelLabel");

// Inspector
const inspectorContent = document.getElementById("inspectorContent");
const inspectorEmptyMsg = document.getElementById("inspectorEmptyMsg");
const propNameInput = document.getElementById("propNameInput");
const propFontSelect = document.getElementById("propFontSelect");
const propFontSizeInput = document.getElementById("propFontSizeInput");
const fontSizeDisplay = document.getElementById("fontSizeDisplay");
const propColorInput = document.getElementById("propColorInput");
const propAlignSelect = document.getElementById("propAlignSelect");
const propAutoShrink = document.getElementById("propAutoShrink");
const propMultiLine = document.getElementById("propMultiLine");
const propIsSignature = document.getElementById("propIsSignature");
const propPrefixInput = document.getElementById("propPrefixInput");
const propSuffixInput = document.getElementById("propSuffixInput");
const deleteItemBtn = document.getElementById("deleteItemBtn");

// Modal
const generateModal = document.getElementById("generateModal");
const progressBarFill = document.getElementById("progressBarFill");
const modalSuccessActions = document.getElementById("modalSuccessActions");
const modalSummaryMsg = document.getElementById("modalSummaryMsg");
const downloadZipLink = document.getElementById("downloadZipLink");
const closeModalBtn = document.getElementById("closeModalBtn");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  fitCanvasToScreen();
  renderCanvas();
});

function setupEventListeners() {
  // Page Count Changer
  pageCountSelect.addEventListener("change", (e) => {
    setPageCount(parseInt(e.target.value, 10));
  });

  // Sheet Changer
  sheetSelect.addEventListener("change", async (e) => {
    if (e.target.value) {
      await switchSheet(e.target.value);
    }
  });

  // Student Navigation
  prevStudentBtn.addEventListener("click", () => navigateStudent(-1));
  nextStudentBtn.addEventListener("click", () => navigateStudent(1));

  // Auto Place
  autoPlaceBtn.addEventListener("click", runAutoPlace);

  // Preview Toggle
  previewToggleBtn.addEventListener("click", togglePreviewMode);

  // Generate
  generateBtn.addEventListener("click", runBulkGenerate);

  // Upload Trigger clicks
  frontUploadCard.addEventListener("click", () => frontFileInput.click());
  backUploadCard.addEventListener("click", () => backFileInput.click());
  excelUploadCard.addEventListener("click", () => excelFileInput.click());
  sigUploadCard.addEventListener("click", () => sigFileInput.click());

  // File Inputs
  frontFileInput.addEventListener("change", (e) => handleFileUpload(e.target.files[0], 0));
  backFileInput.addEventListener("change", (e) => handleFileUpload(e.target.files[0], 1));
  excelFileInput.addEventListener("change", (e) => handleExcelUpload(e.target.files[0]));
  sigFileInput.addEventListener("change", (e) => handleSignatureUpload(e.target.files[0]));

  // Page Tabs
  tabFrontBtn.addEventListener("click", () => switchPage(0));
  tabBackBtn.addEventListener("click", () => switchPage(1));

  // Add Custom Placeholder
  addFieldBtn.addEventListener("click", () => {
    const dim = state.nativeDimensions[state.activePage];
    const newItem = {
      id: Math.random().toString(36).substring(2, 9),
      name: "New Field",
      page_index: state.activePage,
      x: dim.width * 0.25,
      y: dim.height * 0.5,
      width: dim.width * 0.5,
      height: 70,
      font_family: "PTSerif-Bold",
      font_size: 44,
      font_color: "#112354",
      alignment: "center",
      auto_shrink: true,
      is_signature: false,
      prefix: "",
      suffix: ""
    };
    state.items.push(newItem);
    state.selectedItemId = newItem.id;
    renderCanvas();
    renderFieldList();
    updateInspector();
  });

  // Inspector Bindings
  propNameInput.addEventListener("input", (e) => updateSelectedItem({ name: e.target.value }));
  propFontSelect.addEventListener("change", (e) => updateSelectedItem({ font_family: e.target.value }));
  propFontSizeInput.addEventListener("input", (e) => {
    fontSizeDisplay.textContent = e.target.value;
    updateSelectedItem({ font_size: parseInt(e.target.value, 10) });
  });
  propColorInput.addEventListener("input", (e) => updateSelectedItem({ font_color: e.target.value }));
  propAlignSelect.addEventListener("change", (e) => updateSelectedItem({ alignment: e.target.value }));
  propAutoShrink.addEventListener("change", (e) => updateSelectedItem({ auto_shrink: e.target.checked }));
  propMultiLine.addEventListener("change", (e) => updateSelectedItem({ multi_line: e.target.checked, max_lines: e.target.checked ? 2 : 1 }));
  propIsSignature.addEventListener("change", (e) => updateSelectedItem({ is_signature: e.target.checked }));
  propPrefixInput.addEventListener("input", (e) => updateSelectedItem({ prefix: e.target.value }));
  propSuffixInput.addEventListener("input", (e) => updateSelectedItem({ suffix: e.target.value }));

  deleteItemBtn.addEventListener("click", () => {
    if (!state.selectedItemId) return;
    state.items = state.items.filter(it => it.id !== state.selectedItemId);
    state.selectedItemId = null;
    renderCanvas();
    renderFieldList();
    updateInspector();
  });

  // Zoom Controls
  zoomInBtn.addEventListener("click", () => setZoom(state.zoom * 1.15));
  zoomOutBtn.addEventListener("click", () => setZoom(state.zoom / 1.15));
  zoomResetBtn.addEventListener("click", fitCanvasToScreen);

  // Close Modal
  closeModalBtn.addEventListener("click", () => {
    generateModal.style.display = "none";
  });
}

function setPageCount(count) {
  state.pageCount = count;
  pageCountSelect.value = count;
  if (count === 1) {
    backUploadCard.style.display = "none";
    tabBackBtn.style.display = "none";
    if (state.activePage === 1) switchPage(0);
  } else {
    backUploadCard.style.display = "flex";
    tabBackBtn.style.display = "inline-block";
  }
  renderFieldList();
}

function switchPage(pageIdx) {
  state.activePage = pageIdx;
  if (pageIdx === 0) {
    tabFrontBtn.classList.add("active");
    tabBackBtn.classList.remove("active");
    canvasPageIndicator.textContent = "Page 1 (Front)";
  } else {
    tabBackBtn.classList.add("active");
    tabFrontBtn.classList.remove("active");
    canvasPageIndicator.textContent = "Page 2 (Back)";
  }
  state.selectedItemId = null;
  updateInspector();
  renderCanvas();
  renderFieldList();
  if (state.isPreviewMode) renderLivePreview();
}

// Canvas Rendering & Scale
function getCanvasScale() {
  const native = state.nativeDimensions[state.activePage];
  const renderedWidth = parseFloat(canvasStage.style.width);
  return renderedWidth / native.width;
}

function fitCanvasToScreen() {
  const wrapperRect = stageWrapper.getBoundingClientRect();
  const native = state.nativeDimensions[state.activePage];
  const availW = wrapperRect.width - 80;
  const availH = wrapperRect.height - 80;

  const scaleW = availW / native.width;
  const scaleH = availH / native.height;
  const fitScale = Math.min(scaleW, scaleH, 1.0);

  setZoom(fitScale);
}

function setZoom(scale) {
  state.zoom = Math.max(0.15, Math.min(2.5, scale));
  const native = state.nativeDimensions[state.activePage];
  const w = Math.round(native.width * state.zoom);
  const h = Math.round(native.height * state.zoom);

  canvasStage.style.width = `${w}px`;
  canvasStage.style.height = `${h}px`;
  zoomLevelLabel.textContent = `${Math.round(state.zoom * 100)}%`;

  renderCanvas();
}

function renderCanvas() {
  const url = state.templateUrls[state.activePage];
  if (url) {
    canvasBgImage.src = url;
    canvasBgImage.style.display = "block";
    canvasDimLabel.textContent = `(${state.nativeDimensions[state.activePage].width} × ${state.nativeDimensions[state.activePage].height} px)`;
  } else {
    canvasBgImage.style.display = "none";
    canvasDimLabel.textContent = "(No Template Loaded)";
  }

  placeholderLayer.innerHTML = "";
  const scale = getCanvasScale();
  const pageItems = state.items.filter(it => it.page_index === state.activePage);

  pageItems.forEach(item => {
    const el = document.createElement("div");
    el.className = `canvas-item ${item.id === state.selectedItemId ? "selected" : ""}`;
    el.id = `item-${item.id}`;

    // Apply scaled coordinates
    el.style.left = `${item.x * scale}px`;
    el.style.top = `${item.y * scale}px`;
    el.style.width = `${item.width * scale}px`;
    el.style.height = `${item.height * scale}px`;

    // Dynamic label preview with decimal cleanup
    function getCleanVal(row, name) {
      if (!row || !name) return "";
      let val = row[name];
      if (val === undefined || val === null || val === "") {
        const lowerName = name.toLowerCase().replace(/[_\.]/g, " ").trim();
        for (const k of Object.keys(row)) {
          const lowerK = k.toLowerCase().replace(/[_\.]/g, " ").trim();
          if (lowerK === lowerName || lowerK.includes(lowerName) || lowerName.includes(lowerK)) {
            val = row[k];
            break;
          }
        }
      }
      if (val === undefined || val === null) return "";
      let str = String(val).trim();
      if (/^-?\d+\.0+$/.test(str)) {
        str = str.replace(/\.0+$/, "");
      }
      // Format attendance / percentage fields (e.g. 1 -> 100%, 0.85 -> 85%)
      const isPercentField = /attendance|percentage|percent|%/i.test(name);
      if (isPercentField && !str.includes("%")) {
        const num = parseFloat(str);
        if (!isNaN(num)) {
          if (num > 0 && num <= 1.0) {
            str = `${Math.round(num * 100)}%`;
          } else if (num > 1.0 && num <= 100.0) {
            str = `${Math.round(num)}%`;
          }
        }
      }
      return str;
    }

    function splitTwoLines(text) {
      if (!text || text.includes("\n")) return text;
      const words = text.split(/\s+/);
      if (words.length <= 1) return text;
      let bestDiff = Infinity;
      let bestSplit = text;
      for (let i = 1; i < words.length; i++) {
        const l1 = words.slice(0, i).join(" ");
        const l2 = words.slice(i).join(" ");
        const diff = Math.abs(l1.length - l2.length);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestSplit = `${l1}\n${l2}`;
        }
      }
      return bestSplit;
    }

    let displayVal = item.name;
    if (state.excel.sampleRows.length > 0) {
      const row = state.excel.sampleRows[state.studentIndex] || state.excel.sampleRows[0];
      const cleanVal = getCleanVal(row, item.name);
      if (cleanVal) {
        displayVal = `${item.prefix || ""}${cleanVal}${item.suffix || ""}`;
      }
    }

    // Auto-split into 2 lines if multiline is enabled or if it's a project title
    const shouldSplit = (
      displayVal.includes("\n")
      || item.multi_line
      || (item.max_lines && item.max_lines >= 2)
      || (/project|title/i.test(item.name) && displayVal.split(/\s+/).length >= 3)
    );
    if (shouldSplit && !displayVal.includes("\n")) {
      displayVal = splitTwoLines(displayVal);
    }

    el.innerHTML = `
      <span class="item-label" style="color: ${item.font_color}; font-family: ${item.font_family}; font-size: ${Math.max(10, item.font_size * scale)}px; white-space: pre-line; text-align: ${item.alignment}; line-height: 1.25;">
        ${item.is_signature ? "✍️ [Signature]" : displayVal}
      </span>
      <div class="handle handle-nw" data-handle="nw"></div>
      <div class="handle handle-ne" data-handle="ne"></div>
      <div class="handle handle-se" data-handle="se"></div>
      <div class="handle handle-sw" data-handle="sw"></div>
      <div class="handle handle-n" data-handle="n"></div>
      <div class="handle handle-s" data-handle="s"></div>
      <div class="handle handle-w" data-handle="w"></div>
      <div class="handle handle-e" data-handle="e"></div>
    `;

    // Drag & Resize Listeners
    setupDragAndResize(el, item);

    placeholderLayer.appendChild(el);
  });
}

// Drag & Resize Logic
function setupDragAndResize(el, item) {
  el.addEventListener("mousedown", (e) => {
    e.stopPropagation();
    state.selectedItemId = item.id;
    updateInspector();
    renderCanvas();
    renderFieldList();

    const handle = e.target.dataset.handle;
    const scale = getCanvasScale();
    const startX = e.clientX;
    const startY = e.clientY;

    const initialItemX = item.x;
    const initialItemY = item.y;
    const initialItemW = item.width;
    const initialItemH = item.height;

    function onMouseMove(moveEvent) {
      const dx = (moveEvent.clientX - startX) / scale;
      const dy = (moveEvent.clientY - startY) / scale;

      if (!handle) {
        // Dragging whole placeholder
        item.x = Math.max(0, initialItemX + dx);
        item.y = Math.max(0, initialItemY + dy);
      } else {
        // Resizing
        if (handle.includes("e")) item.width = Math.max(40, initialItemW + dx);
        if (handle.includes("s")) item.height = Math.max(20, initialItemH + dy);
        if (handle.includes("w")) {
          const newW = Math.max(40, initialItemW - dx);
          item.x = initialItemX + (initialItemW - newW);
          item.width = newW;
        }
        if (handle.includes("n")) {
          const newH = Math.max(20, initialItemH - dy);
          item.y = initialItemY + (initialItemH - newH);
          item.height = newH;
        }
      }

      // Live update DOM directly for 60fps smoothness
      el.style.left = `${item.x * scale}px`;
      el.style.top = `${item.y * scale}px`;
      el.style.width = `${item.width * scale}px`;
      el.style.height = `${item.height * scale}px`;
    }

    function onMouseUp() {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      renderCanvas();
    }

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });
}

// Deselect when clicking canvas background
stageWrapper.addEventListener("mousedown", (e) => {
  if (e.target === stageWrapper || e.target === canvasStage || e.target === canvasBgImage) {
    state.selectedItemId = null;
    updateInspector();
    renderCanvas();
    renderFieldList();
  }
});

// Field List Panel
function renderFieldList() {
  fieldListContainer.innerHTML = "";
  const pageItems = state.items.filter(it => it.page_index === state.activePage);

  if (pageItems.length === 0) {
    fieldListContainer.innerHTML = `<div style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 12px;">No placeholders on this page yet. Click "+ Add" or "⚡ Auto Place".</div>`;
    return;
  }

  pageItems.forEach(it => {
    const chip = document.createElement("div");
    chip.className = `field-chip ${it.id === state.selectedItemId ? "selected" : ""}`;
    chip.innerHTML = `
      <span>${it.is_signature ? "✍️ Signature" : it.name}</span>
      <button class="del-btn" title="Delete">×</button>
    `;

    chip.addEventListener("click", () => {
      state.selectedItemId = it.id;
      renderCanvas();
      renderFieldList();
      updateInspector();
    });

    chip.querySelector(".del-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      state.items = state.items.filter(x => x.id !== it.id);
      if (state.selectedItemId === it.id) state.selectedItemId = null;
      renderCanvas();
      renderFieldList();
      updateInspector();
    });

    fieldListContainer.appendChild(chip);
  });
}

// Property Inspector
function updateInspector() {
  const item = state.items.find(it => it.id === state.selectedItemId);
  if (!item) {
    inspectorContent.style.display = "none";
    inspectorEmptyMsg.style.display = "block";
    return;
  }

  inspectorContent.style.display = "block";
  inspectorEmptyMsg.style.display = "none";

  propNameInput.value = item.name;
  propFontSelect.value = item.font_family;
  propFontSizeInput.value = item.font_size;
  fontSizeDisplay.textContent = item.font_size;
  propColorInput.value = item.font_color.startsWith("#") ? item.font_color : "#112354";
  propAlignSelect.value = item.alignment;
  propAutoShrink.checked = item.auto_shrink;
  propMultiLine.checked = !!(item.multi_line || item.max_lines >= 2);
  propIsSignature.checked = item.is_signature;
  propPrefixInput.value = item.prefix || "";
  propSuffixInput.value = item.suffix || "";
}

function updateSelectedItem(updates) {
  const item = state.items.find(it => it.id === state.selectedItemId);
  if (!item) return;
  Object.assign(item, updates);
  renderCanvas();
  renderFieldList();
}

// Upload Handlers
async function handleFileUpload(file, pageIndex) {
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("page_index", pageIndex);

  try {
    const res = await fetch("/api/upload/template", { method: "POST", body: formData });
    const data = await res.json();
    if (res.ok) {
      state.templateUrls[0] = data.front_url;
      state.nativeDimensions[0] = data.dimensions;
      document.getElementById("frontUploadTitle").textContent = file.name;
      frontUploadCard.classList.add("loaded");

      if (data.back_url) {
        state.templateUrls[1] = data.back_url;
        document.getElementById("backUploadTitle").textContent = "Page 2 (Extracted)";
        backUploadCard.classList.add("loaded");
      }

      if (data.detected_pages > 1 && state.pageCount === 1) {
        if (confirm("Uploaded PDF contains multiple pages. Would you like to switch to 2-Page mode?")) {
          setPageCount(2);
        }
      }

      fitCanvasToScreen();
      renderCanvas();
    } else {
      alert(`Error uploading template: ${data.detail}`);
    }
  } catch (err) {
    alert(`Failed to upload: ${err.message}`);
  }
}

async function handleExcelUpload(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload/excel", { method: "POST", body: formData });
    const data = await res.json();
    if (res.ok) {
      state.excel.sheets = data.sheets;
      state.excel.activeSheet = data.active_sheet;
      state.excel.totalStudents = data.total_students;
      state.excel.sampleRows = data.sample_rows;
      state.excel.columns = data.columns;

      document.getElementById("excelUploadTitle").textContent = file.name;
      document.getElementById("excelUploadSub").textContent = `${data.sheets.length} Sheets | ${data.total_students} Students`;
      excelUploadCard.classList.add("loaded");

      // Update Sheet Dropdown
      sheetSelect.innerHTML = "";
      data.sheets.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s;
        opt.textContent = s;
        sheetSelect.appendChild(opt);
      });
      sheetSelect.value = data.active_sheet;

      state.studentIndex = 0;
      updateStudentNav();
      renderCanvas();
    } else {
      alert(`Excel error: ${data.detail}`);
    }
  } catch (err) {
    alert(`Failed to upload Excel: ${err.message}`);
  }
}

async function switchSheet(sheetName) {
  try {
    const res = await fetch("/api/excel/sheet", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sheet_name: sheetName })
    });
    const data = await res.json();
    if (res.ok) {
      state.excel.activeSheet = data.active_sheet;
      state.excel.totalStudents = data.total_students;
      state.excel.sampleRows = data.sample_rows;
      state.excel.columns = data.columns;

      state.studentIndex = 0;
      updateStudentNav();
      renderCanvas();
      if (state.isPreviewMode) renderLivePreview();
    }
  } catch (err) {
    alert(`Error switching sheet: ${err.message}`);
  }
}

async function handleSignatureUpload(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/api/upload/signature", { method: "POST", body: formData });
    const data = await res.json();
    if (res.ok) {
      document.getElementById("sigUploadTitle").textContent = file.name;
      sigUploadCard.classList.add("loaded");
      alert("Signature uploaded! Click '⚡ Auto Place' or add a placeholder with 'Is Signature Stamp' enabled.");
    }
  } catch (err) {
    alert(`Error uploading signature: ${err.message}`);
  }
}

// Student Navigator
function updateStudentNav() {
  if (state.excel.totalStudents === 0) {
    studentNavLabel.textContent = "No Students";
    prevStudentBtn.disabled = true;
    nextStudentBtn.disabled = true;
    return;
  }

  const row = state.excel.sampleRows[state.studentIndex] || {};
  const name = row.Name || row["Student Name"] || "Student";
  studentNavLabel.textContent = `${state.studentIndex + 1}/${state.excel.totalStudents}: ${name}`;
  prevStudentBtn.disabled = state.studentIndex <= 0;
  nextStudentBtn.disabled = state.studentIndex >= state.excel.totalStudents - 1;
}

function navigateStudent(delta) {
  const newIdx = state.studentIndex + delta;
  if (newIdx >= 0 && newIdx < state.excel.totalStudents) {
    state.studentIndex = newIdx;
    updateStudentNav();
    renderCanvas();
    if (state.isPreviewMode) renderLivePreview();
  }
}

// Auto Place
async function runAutoPlace() {
  try {
    const res = await fetch("/api/auto-place");
    const data = await res.json();
    if (res.ok && data.items) {
      state.items = data.items;
      renderCanvas();
      renderFieldList();
      updateInspector();
    }
  } catch (err) {
    alert(`Auto-place error: ${err.message}`);
  }
}

// Live Preview
async function togglePreviewMode() {
  state.isPreviewMode = !state.isPreviewMode;
  if (state.isPreviewMode) {
    previewToggleBtn.textContent = "✏️ Canvas Editor";
    previewToggleBtn.classList.add("btn-primary");
    canvasStage.style.display = "none";
    previewContainer.style.display = "flex";
    await renderLivePreview();
  } else {
    previewToggleBtn.textContent = "👁️ Live Preview";
    previewToggleBtn.classList.remove("btn-primary");
    canvasStage.style.display = "block";
    previewContainer.style.display = "none";
  }
}

async function renderLivePreview() {
  try {
    const payload = {
      page_index: state.activePage,
      student_index: state.studentIndex,
      page_count: state.pageCount,
      selected_sheet: state.excel.activeSheet,
      items: state.items
    };

    const res = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      previewImg.src = data.preview_b64;
    }
  } catch (err) {
    console.error("Preview error:", err);
  }
}

// Bulk Generation
async function runBulkGenerate() {
  if (state.items.length === 0) {
    alert("Please add at least one placeholder before generating certificates.");
    return;
  }
  if (!state.templateUrls[0]) {
    alert("Please upload the Front Template first.");
    return;
  }
  if (state.excel.totalStudents === 0) {
    alert("Please upload student data in an Excel file first.");
    return;
  }

  // Open progress modal
  generateModal.style.display = "flex";
  modalSuccessActions.style.display = "none";
  progressBarFill.style.width = "25%";

  try {
    const payload = {
      page_count: state.pageCount,
      selected_sheet: state.excel.activeSheet,
      generate_all_sheets: false,
      naming_pattern: "{Register No}_{Name}.pdf",
      items: state.items
    };

    progressBarFill.style.width = "65%";
    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok) {
      progressBarFill.style.width = "100%";
      modalSummaryMsg.textContent = `✓ Generated ${data.total_generated} high-resolution PDF certificates!`;
      downloadZipLink.href = data.download_zip_url;
      modalSuccessActions.style.display = "block";
    } else {
      alert(`Generation error: ${data.detail}`);
      generateModal.style.display = "none";
    }
  } catch (err) {
    alert(`Bulk generation failed: ${err.message}`);
    generateModal.style.display = "none";
  }
}

// Android PWA Install Event Handler
let deferredPrompt;
const pwaInstallBtn = document.getElementById("pwaInstallBtn");

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  if (pwaInstallBtn) {
    pwaInstallBtn.style.display = "inline-flex";
  }
});

if (pwaInstallBtn) {
  pwaInstallBtn.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    console.log("[PWA] User response to install:", outcome);
    deferredPrompt = null;
    pwaInstallBtn.style.display = "none";
  });
}

window.addEventListener("appinstalled", () => {
  console.log("[PWA] App successfully installed on device!");
  if (pwaInstallBtn) pwaInstallBtn.style.display = "none";
});
