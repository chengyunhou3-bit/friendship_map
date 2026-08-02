import streamlit as st


COMPONENT_HTML = """
<span id="pin-keyboard-listener" aria-hidden="true"></span>
"""


COMPONENT_CSS = """
#pin-keyboard-listener {
  display: none;
}
"""


COMPONENT_JS = """
export default function(component) {
  const appDocument = component.parentElement.ownerDocument;
  const { data, setTriggerValue } = component;
  let eventSequence = 0;
  let pinValue = typeof data?.currentPin === "string"
    ? data.currentPin.replace(/\\D/g, "").slice(0, 8)
    : "";

  const handleKeyDown = (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.repeat) return;

    const supportedKeys = ["Backspace", "Enter", "Escape"];
    const isDigit = /^[0-9]$/.test(event.key);
    if (!isDigit && !supportedKeys.includes(event.key)) return;

    event.preventDefault();

    if (isDigit && pinValue.length < 8) {
      pinValue += event.key;
    } else if (event.key === "Backspace") {
      pinValue = pinValue.slice(0, -1);
    }

    eventSequence += 1;
    setTriggerValue("key", {
      key: event.key,
      value: pinValue,
      eventId: `${Date.now()}-${eventSequence}`
    });
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
