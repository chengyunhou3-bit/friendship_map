import streamlit as st


COMPONENT_HTML = """
<div class="notes-editor">
  <div class="notes-header"><span>對象</span><span>備註／定義</span></div>
  <div id="notes-rows"></div>
  <button id="add-note" class="add-note" type="button" aria-label="新增一列">＋</button>
  <button id="save-notes" class="save-notes" type="button">保存備註</button>
  <span id="notes-status" class="notes-status"></span>
</div>
"""


COMPONENT_CSS = """
.notes-editor { width:100%; height:100%; overflow-y:auto; box-sizing:border-box; padding-left:.85rem; font-family:var(--st-font); }
.notes-header, .note-row { display:grid; grid-template-columns:minmax(10rem, .8fr) minmax(14rem, 1.4fr); }
.notes-header { color:color-mix(in srgb,var(--st-text-color) 72%,transparent); font-size:.86rem; font-weight:650; }
.notes-header span { padding:.45rem .7rem; }
.note-row { position:relative; margin-bottom:.4rem; border:1px solid color-mix(in srgb,var(--st-text-color) 18%,transparent); border-radius:.55rem; background:var(--st-secondary-background-color); }
.note-cell { padding:.35rem; min-width:0; }
.note-cell + .note-cell { border-left:1px solid color-mix(in srgb,var(--st-text-color) 14%,transparent); }
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
@media (max-width:560px) { .notes-header { display:none; } .note-row { grid-template-columns:1fr; } .note-cell + .note-cell { border-left:0; border-top:1px solid color-mix(in srgb,var(--st-text-color) 14%,transparent); } }
"""


COMPONENT_JS = """
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const rowsRoot = parentElement.querySelector("#notes-rows");
  const addButton = parentElement.querySelector("#add-note");
  const saveButton = parentElement.querySelector("#save-notes");
  const status = parentElement.querySelector("#notes-status");
  const options = Array.isArray(data?.options) ? data.options : [];
  let rows = (Array.isArray(data?.rows) ? data.rows : []).map((row) => ({...row}));

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
      remove.setAttribute("aria-label", "刪除此列");
      remove.onclick = () => { rows.splice(index, 1); render(); };
      rowElement.appendChild(remove);

      const targetCell = make("div", "note-cell");
      if (row.mode === "custom") {
        const wrap = make("div", "custom-wrap");
        const back = make("button", "back-select");
        back.type = "button";
        back.textContent = "⌄";
        back.title = "返回選單";
        back.onclick = () => { row.mode = "option"; row.target = ""; render(); };
        const input = make("input");
        input.type = "text";
        input.maxLength = 80;
        input.placeholder = "輸入自訂對象";
        input.value = row.custom || "";
        input.oninput = () => { row.custom = input.value; };
        wrap.append(back, input);
        targetCell.appendChild(wrap);
      } else {
        const select = make("select");
        const placeholder = document.createElement("option");
        placeholder.value = "";
        placeholder.textContent = "選擇對象";
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
      noteInput.placeholder = "輸入備註或定義";
      noteInput.value = row.note || "";
      noteInput.oninput = () => { row.note = noteInput.value; };
      noteCell.appendChild(noteInput);
      rowElement.append(targetCell, noteCell);
      rowsRoot.appendChild(rowElement);
    });
  };

  addButton.onclick = () => { rows.push({mode:"option", target:"", custom:"", note:""}); render(); };
  saveButton.onclick = () => {
    const cleaned = rows.filter((row) => row.target || row.custom || row.note);
    const invalid = cleaned.some((row) => !(row.note || "").trim() || (row.mode === "custom" ? !(row.custom || "").trim() : !row.target));
    status.className = "notes-status";
    if (invalid) {
      status.textContent = "每列都需要對象與備註。";
      status.classList.add("error");
      return;
    }
    rows = cleaned;
    status.textContent = "已保存。";
    setTriggerValue("saved", { rows });
    render();
  };
  render();
  return () => { addButton.onclick = null; saveButton.onclick = null; };
}
"""


notes_editor = st.components.v2.component(
    "notes_editor",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
