import streamlit as st


COMPONENT_HTML = """
<div
  id="pin-keyboard-display"
  role="textbox"
  aria-label="PIN 輸入"
  aria-live="polite"
></div>
<div id="pin-keypad" class="pin-keypad" aria-label="PIN 數字鍵盤">
  <button type="button" data-digit="1">1</button><button type="button" data-digit="2">2</button><button type="button" data-digit="3">3</button>
  <button type="button" data-digit="4">4</button><button type="button" data-digit="5">5</button><button type="button" data-digit="6">6</button>
  <button type="button" data-digit="7">7</button><button type="button" data-digit="8">8</button><button type="button" data-digit="9">9</button>
  <button id="pin-backspace" type="button" aria-label="刪除一位">⌫</button><button type="button" data-digit="0">0</button><button id="pin-confirm" class="pin-confirm" type="button" aria-label="確認">✓</button>
</div>
<button id="pin-cancel" class="pin-cancel" type="button">取消</button>
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

.pin-keypad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-top: 0.65rem;
}

.pin-keypad button,
.pin-cancel {
  min-height: 3rem;
  border: 1px solid color-mix(in srgb, var(--st-text-color) 22%, transparent);
  border-radius: 0.55rem;
  color: var(--st-text-color);
  background: var(--st-secondary-background-color);
  font: inherit;
  font-size: 1.15rem;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.pin-keypad button:active,
.pin-cancel:active {
  transform: scale(0.97);
  filter: brightness(0.94);
}

.pin-keypad .pin-confirm {
  border-color: var(--st-primary-color);
  color: white;
  background: var(--st-primary-color);
}

.pin-cancel {
  width: 100%;
  margin-top: 0.65rem;
}
"""


COMPONENT_JS = """
export default function(component) {
  const appDocument = component.parentElement.ownerDocument;
  const { data, setTriggerValue } = component;
  const display = component.parentElement.querySelector(
    "#pin-keyboard-display"
  );
  const digitButtons = component.parentElement.querySelectorAll(
    "[data-digit]"
  );
  const backspaceButton = component.parentElement.querySelector(
    "#pin-backspace"
  );
  const confirmButton = component.parentElement.querySelector(
    "#pin-confirm"
  );
  const cancelButton = component.parentElement.querySelector("#pin-cancel");
  const keypad = component.parentElement.querySelector("#pin-keypad");
  const isEnglish = data?.language === "en";
  display.setAttribute("aria-label", isEnglish ? "PIN input" : "PIN 輸入");
  keypad.setAttribute("aria-label", isEnglish ? "PIN keypad" : "PIN 數字鍵盤");
  backspaceButton.setAttribute("aria-label", isEnglish ? "Delete one digit" : "刪除一位");
  confirmButton.setAttribute("aria-label", isEnglish ? "Confirm" : "確認");
  cancelButton.textContent = isEnglish ? "Cancel" : "取消";
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
      : (isEnglish ? "Enter PIN" : "請輸入 PIN");
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

  const addDigit = (digit) => {
    if (submitted || pinValue.length >= 8) return;
    pinValue += digit;
    updateDisplay();
    if (
      expectedLength >= 4
      && expectedLength <= 8
      && pinValue.length === expectedLength
    ) {
      sendAction("submit");
    }
  };

  digitButtons.forEach((button) => {
    button.onclick = () => addDigit(button.dataset.digit);
  });
  backspaceButton.onclick = () => {
    if (submitted) return;
    pinValue = pinValue.slice(0, -1);
    updateDisplay();
  };
  confirmButton.onclick = () => sendAction("submit");
  cancelButton.onclick = () => sendAction("cancel");

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
      addDigit(event.key);
      return;
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
  };

  appDocument.addEventListener("keydown", handleKeyDown);

  return () => {
    appDocument.removeEventListener("keydown", handleKeyDown);
    digitButtons.forEach((button) => { button.onclick = null; });
    backspaceButton.onclick = null;
    confirmButton.onclick = null;
    cancelButton.onclick = null;
  };
}
"""


pin_keyboard_listener = st.components.v2.component(
    "pin_keyboard_listener",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
