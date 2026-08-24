import streamlit as st


COMPONENT_HTML = """
<div class="comparison-keyboard-hint" aria-live="polite">
  <span id="left-hint"><kbd>←</kbd>／<kbd>A</kbd> 左邊</span>
  <span id="equal-hint"><kbd>↓</kbd>／<kbd>S</kbd> 一樣</span>
  <span id="right-hint"><kbd>→</kbd>／<kbd>D</kbd> 右邊</span>
</div>
"""


COMPONENT_CSS = """
.comparison-keyboard-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  box-sizing: border-box;
  width: 100%;
  min-height: 2.5rem;
  color: color-mix(in srgb, var(--st-text-color) 72%, transparent);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang TC", sans-serif;
  font-size: 0.88rem;
}

kbd {
  display: inline-block;
  min-width: 1.35rem;
  padding: 0.08rem 0.28rem;
  border: 1px solid color-mix(in srgb, var(--st-text-color) 25%, transparent);
  border-radius: 0.3rem;
  background: var(--st-secondary-background-color);
  color: var(--st-text-color);
  font: inherit;
  font-weight: 650;
  text-align: center;
}

@media (max-width: 520px) {
  .comparison-keyboard-hint {
    gap: 0.45rem;
    font-size: 0.78rem;
  }
}
"""


COMPONENT_JS = """
export default function(component) {
  const appDocument = component.parentElement.ownerDocument;
  const { data, parentElement, setTriggerValue } = component;
  const isEnglish = data?.language === "en";
  parentElement.querySelector("#left-hint").lastChild.textContent = isEnglish ? " Left" : " 左邊";
  parentElement.querySelector("#equal-hint").lastChild.textContent = isEnglish ? " Equal" : " 一樣";
  parentElement.querySelector("#right-hint").lastChild.textContent = isEnglish ? " Right" : " 右邊";
  let submitted = false;
  let eventSequence = 0;

  const keyChoices = {
    ArrowLeft: ">",
    a: ">",
    ArrowDown: "=",
    s: "=",
    ArrowRight: "<",
    d: "<"
  };

  const handleKeyDown = (event) => {
    if (
      submitted
      || event.repeat
      || event.ctrlKey
      || event.metaKey
      || event.altKey
    ) return;

    const target = event.target;
    const targetTag = String(target?.tagName || "").toUpperCase();
    if (
      target?.isContentEditable
      || targetTag === "INPUT"
      || targetTag === "TEXTAREA"
      || targetTag === "SELECT"
    ) return;

    const normalizedKey = event.key.length === 1
      ? event.key.toLowerCase()
      : event.key;
    const choice = keyChoices[normalizedKey];
    if (!choice) return;

    event.preventDefault();
    submitted = true;
    eventSequence += 1;
    setTriggerValue("action", {
      choice,
      eventId: `${Date.now()}-${eventSequence}`
    });
  };

  appDocument.addEventListener("keydown", handleKeyDown);

  return () => {
    appDocument.removeEventListener("keydown", handleKeyDown);
  };
}
"""


comparison_keyboard_listener = st.components.v2.component(
    "comparison_keyboard_listener",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
