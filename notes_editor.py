import streamlit as st


COMPONENT_HTML = """
<div class="notes-editor">
  <div class="notes-header"><span id="order-heading" class="order-heading" title="拖曳排序">↕</span><span id="target-heading">對象</span><span id="note-heading">備註／定義</span></div>
  <div id="notes-rows"></div>
  <button id="add-note" class="add-note" type="button" aria-label="新增一列">＋</button>
  <button id="save-notes" class="save-notes" type="button">保存備註</button>
  <span id="notes-status" class="notes-status"></span>
  <dialog id="delete-dialog" class="delete-dialog">
    <p id="delete-message">確定要刪除這一列備註嗎？</p>
    <div class="dialog-actions">
      <button id="cancel-delete" type="button">取消</button>
      <button id="confirm-delete" class="confirm-delete" type="button">刪除</button>
    </div>
  </dialog>
</div>
"""


COMPONENT_CSS = """
.notes-editor { width:100%; height:100%; overflow-y:auto; box-sizing:border-box; padding-left:.85rem; font-family:var(--st-font); }
.notes-header, .note-row { display:grid; grid-template-columns:2.25rem minmax(10rem, .8fr) minmax(14rem, 1.4fr); }
.notes-header { color:color-mix(in srgb,var(--st-text-color) 72%,transparent); font-size:.86rem; font-weight:650; }
.notes-header span { padding:.45rem .7rem; }
.note-row { position:relative; margin-bottom:.4rem; border:1px solid color-mix(in srgb,var(--st-text-color) 18%,transparent); border-radius:.55rem; background:var(--st-secondary-background-color); }
.note-cell { padding:.35rem; min-width:0; }
.note-cell + .note-cell { border-left:1px solid color-mix(in srgb,var(--st-text-color) 14%,transparent); }
.drag-cell { display:flex; align-items:center; justify-content:center; border-right:1px solid color-mix(in srgb,var(--st-text-color) 14%,transparent); }
.order-heading { display:flex; align-items:center; justify-content:center; padding:.45rem 0 !important; font-size:1rem; }
.drag-handle { display:grid; grid-template-columns:repeat(2,.28rem); grid-template-rows:repeat(3,.28rem); gap:.18rem; align-content:center; justify-content:center; width:1.7rem; height:2rem; border:1px solid color-mix(in srgb,var(--st-text-color) 24%,transparent); border-radius:.4rem; padding:0; color:var(--st-text-color); background:var(--st-background-color); cursor:grab; user-select:none; box-shadow:0 1px 2px rgba(0,0,0,.12); }
.grip-dot { display:block; width:.28rem; height:.28rem; border-radius:50%; background:currentColor; opacity:.7; }
.drag-handle:hover { border-color:var(--st-primary-color); color:var(--st-primary-color); }
.drag-handle:active { cursor:grabbing; }
.note-row.dragging { opacity:.45; }
.note-row.drag-over { outline:2px solid var(--st-primary-color); }
select, input { width:100%; min-height:2.45rem; box-sizing:border-box; border:0; border-radius:.35rem; padding:.45rem .55rem; color:var(--st-text-color); background:var(--st-background-color); font:inherit; }
select:focus, input:focus { outline:2px solid var(--st-primary-color); }
.custom-wrap { display:flex; gap:.3rem; }
.back-select { flex:0 0 2.4rem; width:2.4rem; border:0; border-radius:.35rem; color:var(--st-text-color); background:var(--st-background-color); cursor:pointer; }
.remove-note { position:absolute; left:-.72rem; top:50%; translate:0 -50%; width:1.45rem; height:1.45rem; padding:0; border:0; border-radius:50%; opacity:0; color:white; background:#d9534f; font-size:1.15rem; line-height:1; cursor:pointer; transition:opacity .15s; z-index:2; }
.note-row:hover .remove-note, .remove-note:focus { opacity:1; }
.add-note { width:100%; min-height:2.35rem; border:1px dashed color-mix(in srgb,var(--st-text-color) 35%,transparent); border-radius:.5rem; color:var(--st-text-color); background:transparent; font-size:1.3rem; cursor:pointer; }
.save-notes { width:100%; margin-top:.75rem; min-height:2.6rem; border:0; border-radius:.5rem; color:white; background:var(--st-primary-color); font:inherit; font-weight:650; cursor:pointer; }
.notes-status { display:block; min-height:1.3rem; margin-top:.35rem; font-size:.88rem; }
.notes-status.error { color:#ff6b6b; }
.delete-dialog { width:min(22rem,calc(100% - 2rem)); border:1px solid color-mix(in srgb,var(--st-text-color) 22%,transparent); border-radius:.75rem; padding:1.1rem; color:var(--st-text-color); background:var(--st-background-color); box-shadow:0 12px 38px rgba(0,0,0,.35); }
.delete-dialog::backdrop { background:rgba(0,0,0,.5); }
.delete-dialog p { margin:.1rem 0 1rem; }
.dialog-actions { display:flex; justify-content:flex-end; gap:.55rem; }
.dialog-actions button { border:1px solid color-mix(in srgb,var(--st-text-color) 22%,transparent); border-radius:.45rem; padding:.45rem .85rem; color:var(--st-text-color); background:var(--st-secondary-background-color); font:inherit; cursor:pointer; }
.dialog-actions .confirm-delete { border-color:#d9534f; color:white; background:#d9534f; }
@media (max-width:560px) { .notes-header { display:none; } .note-row { grid-template-columns:2.25rem 1fr; } .drag-cell { grid-row:1 / span 2; } .note-cell + .note-cell { border-left:0; border-top:1px solid color-mix(in srgb,var(--st-text-color) 14%,transparent); } }
"""


COMPONENT_JS = """
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const rowsRoot = parentElement.querySelector("#notes-rows");
  const addButton = parentElement.querySelector("#add-note");
  const saveButton = parentElement.querySelector("#save-notes");
  const status = parentElement.querySelector("#notes-status");
  const deleteDialog = parentElement.querySelector("#delete-dialog");
  const cancelDelete = parentElement.querySelector("#cancel-delete");
  const confirmDelete = parentElement.querySelector("#confirm-delete");
  const options = Array.isArray(data?.options) ? data.options : [];
  const isEnglish = data?.language === "en";
  const labels = isEnglish ? {
    order: "Drag to reorder",
    target: "Target",
    note: "Note / definition",
    add: "Add row",
    save: "Save notes",
    deleteMessage: "Delete this note row?",
    cancel: "Cancel",
    delete: "Delete",
    remove: "Delete row",
    back: "Back to options",
    customPlaceholder: "Enter a custom target",
    selectPlaceholder: "Select a target",
    notePlaceholder: "Enter a note or definition",
    invalid: "Each row needs a target and a note.",
    saved: "Saved."
  } : {
    order: "拖曳排序",
    target: "對象",
    note: "備註／定義",
    add: "新增一列",
    save: "保存備註",
    deleteMessage: "確定要刪除這一列備註嗎？",
    cancel: "取消",
    delete: "刪除",
    remove: "刪除此列",
    back: "返回選單",
    customPlaceholder: "輸入自訂對象",
    selectPlaceholder: "選擇對象",
    notePlaceholder: "輸入備註或定義",
    invalid: "每列都需要對象與備註。",
    saved: "已保存。"
  };
  const orderHeading = parentElement.querySelector("#order-heading");
  orderHeading.title = labels.order;
  parentElement.querySelector("#target-heading").textContent = labels.target;
  parentElement.querySelector("#note-heading").textContent = labels.note;
  addButton.setAttribute("aria-label", labels.add);
  saveButton.textContent = labels.save;
  parentElement.querySelector("#delete-message").textContent = labels.deleteMessage;
  cancelDelete.textContent = labels.cancel;
  confirmDelete.textContent = labels.delete;
  let rows = (Array.isArray(data?.rows) ? data.rows : []).map((row) => ({...row}));
  let pendingDeleteIndex = null;
  let draggedIndex = null;

  const make = (tag, className) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    return element;
  };

  const render = () => {
    rowsRoot.replaceChildren();
    rows.forEach((row, index) => {
      const rowElement = make("div", "note-row");
      const remove = make("button", "remove-note");
      remove.type = "button";
      remove.textContent = "−";
      remove.setAttribute("aria-label", labels.remove);
      remove.onclick = () => {
        pendingDeleteIndex = index;
        deleteDialog.showModal();
      };
      rowElement.appendChild(remove);

      const dragCell = make("div", "drag-cell");
      const dragHandle = make("button", "drag-handle");
      dragHandle.type = "button";
      for (let dotIndex = 0; dotIndex < 6; dotIndex += 1) {
        dragHandle.appendChild(make("span", "grip-dot"));
      }
      dragHandle.title = labels.order;
      dragHandle.setAttribute("aria-label", labels.order);
      dragHandle.draggable = true;
      dragHandle.ondragstart = (event) => {
        draggedIndex = index;
        rowElement.classList.add("dragging");
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(index));
      };
      dragHandle.ondragend = () => {
        draggedIndex = null;
        rowElement.classList.remove("dragging");
        parentElement.querySelectorAll(".drag-over").forEach((item) => item.classList.remove("drag-over"));
      };
      dragCell.appendChild(dragHandle);
      rowElement.appendChild(dragCell);
      rowElement.ondragover = (event) => {
        if (draggedIndex === null || draggedIndex === index) return;
        event.preventDefault();
        rowElement.classList.add("drag-over");
      };
      rowElement.ondragleave = () => rowElement.classList.remove("drag-over");
      rowElement.ondrop = (event) => {
        event.preventDefault();
        rowElement.classList.remove("drag-over");
        if (draggedIndex === null || draggedIndex === index) return;
        const [movedRow] = rows.splice(draggedIndex, 1);
        const destination = draggedIndex < index ? index - 1 : index;
        rows.splice(destination, 0, movedRow);
        draggedIndex = null;
        render();
      };

      const targetCell = make("div", "note-cell");
      if (row.mode === "custom") {
        const wrap = make("div", "custom-wrap");
        const back = make("button", "back-select");
        back.type = "button";
        back.textContent = "⌄";
        back.title = labels.back;
        back.onclick = () => { row.mode = "option"; row.target = ""; render(); };
        const input = make("input");
        input.type = "text";
        input.maxLength = 80;
        input.placeholder = labels.customPlaceholder;
        input.value = row.custom || "";
        input.oninput = () => { row.custom = input.value; };
        wrap.append(back, input);
        targetCell.appendChild(wrap);
      } else {
        const select = make("select");
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = labels.selectPlaceholder;
        placeholder.disabled = true;
        placeholder.selected = !row.target;
        select.appendChild(placeholder);
        options.forEach((option) => {
          const item = document.createElement("option");
          item.value = option.value;
          item.textContent = option.label;
          item.selected = row.target === option.value;
          select.appendChild(item);
        });
        select.onchange = () => {
          if (select.value === "custom") {
            row.mode = "custom";
            row.target = "";
            render();
          } else {
            row.target = select.value;
          }
        };
        targetCell.appendChild(select);
      }

      const noteCell = make("div", "note-cell");
      const noteInput = make("input");
      noteInput.type = "text";
      noteInput.maxLength = 500;
      noteInput.placeholder = labels.notePlaceholder;
      noteInput.value = row.note || "";
      noteInput.oninput = () => { row.note = noteInput.value; };
      noteCell.appendChild(noteInput);
      rowElement.append(targetCell, noteCell);
      rowsRoot.appendChild(rowElement);
    });
  };

  addButton.onclick = () => { rows.push({mode:"option", target:"", custom:"", note:""}); render(); };
  cancelDelete.onclick = () => {
    pendingDeleteIndex = null;
    deleteDialog.close();
  };
  confirmDelete.onclick = () => {
    if (pendingDeleteIndex !== null) rows.splice(pendingDeleteIndex, 1);
    pendingDeleteIndex = null;
    deleteDialog.close();
    render();
  };
  saveButton.onclick = () => {
    const cleaned = rows.filter((row) => row.target || row.custom || row.note);
    const invalid = cleaned.some((row) => !(row.note || "").trim() || (row.mode === "custom" ? !(row.custom || "").trim() : !row.target));
    status.className = "notes-status";
    if (invalid) {
      status.textContent = labels.invalid;
      status.classList.add("error");
      return;
    }
    rows = cleaned;
    status.textContent = labels.saved;
    setTriggerValue("saved", { rows });
    render();
  };
  render();
  return () => {
    addButton.onclick = null;
    saveButton.onclick = null;
    cancelDelete.onclick = null;
    confirmDelete.onclick = null;
  };
}
"""


notes_editor = st.components.v2.component(
    "notes_editor",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
