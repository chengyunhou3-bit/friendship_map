import streamlit as st


COMPONENT_HTML = """
<div
  id="pin-keyboard-display"
  role="textbox"
  aria-label="PIN 輸入"
  aria-live="polite"
></div>
"""


COMPONENT_CSS = """
#pin-keyboard-display {
  display: flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 100%;
  min-height: 3.4rem;
  padding: 0.8rem;
  border: 1px solid color-mix(in srgb, var(--st-text-color) 28%, transparent);
  border-radius: 0.6rem;
  color: var(--st-text-color);
  background: var(--st-secondary-background-color);
  font-size: 1.4rem;
  letter-spacing: 0.2rem;
}
"""


COMPONENT_JS = """
export default function(component) {
  const appDocument = component.parentElement.ownerDocument;
  const { data, setTriggerValue } = component;
  const display = component.parentElement.querySelector(
    "#pin-keyboard-display"
  );
  let eventSequence = 0;
  let submitted = false;
  let pinValue = typeof data?.currentPin === "string"
    ? data.currentPin.replace(/\\D/g, "").slice(0, 8)
    : "";
  const expectedLength = Number.isInteger(Number(data?.expectedLength))
    ? Number(data.expectedLength)
    : null;

  const updateDisplay = () => {
    display.textContent = pinValue.length > 0
      ? "● ".repeat(pinValue.length).trim()
      : "請輸入 PIN";
  };

  const sendAction = (type) => {
    if (submitted) return;
    submitted = true;
    eventSequence += 1;
    setTriggerValue("action", {
      type,
      value: pinValue,
      eventId: `${Date.now()}-${eventSequence}`
    });
  };

  updateDisplay();

  const handleKeyDown = (event) => {
    if (
      submitted
      || event.ctrlKey
      || event.metaKey
      || event.altKey
      || event.repeat
    ) return;

    const supportedKeys = ["Backspace", "Enter", "Escape"];
    const isDigit = /^[0-9]$/.test(event.key);
    if (!isDigit && !supportedKeys.includes(event.key)) return;

    event.preventDefault();

    if (isDigit && pinValue.length < 8) {
      pinValue += event.key;
    } else if (event.key === "Backspace") {
      pinValue = pinValue.slice(0, -1);
    } else if (event.key === "Enter") {
      sendAction("submit");
      return;
    } else if (event.key === "Escape") {
      sendAction("cancel");
      return;
    }

    updateDisplay();

    if (
      isDigit
      && expectedLength >= 4
      && expectedLength <= 8
      && pinValue.length === expectedLength
    ) {
      sendAction("submit");
    }
  };

  appDocument.addEventListener("keydown", handleKeyDown);

  return () => {
    appDocument.removeEventListener("keydown", handleKeyDown);
  };
}
"""


pin_keyboard_listener = st.components.v2.component(
    "pin_keyboard_listener",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
