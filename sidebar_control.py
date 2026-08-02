import streamlit as st


COMPONENT_HTML = """
<span id="sidebar-control" aria-hidden="true"></span>
"""


COMPONENT_CSS = """
#sidebar-control {
  display: none;
}
"""


COMPONENT_JS = """
export default function(component) {
  const appDocument = component.parentElement.ownerDocument;
  const timers = [];
  let didCollapse = false;

  const collapseSidebar = () => {
    if (didCollapse) return true;

    const collapseButtonContainer = appDocument.querySelector(
      '[data-testid="stSidebarCollapseButton"]'
    );
    const collapseButton = collapseButtonContainer?.matches("button")
      ? collapseButtonContainer
      : collapseButtonContainer?.querySelector("button");

    if (!collapseButton) return false;
    didCollapse = true;
    collapseButton.click();
    return true;
  };

  [0, 120, 350].forEach((delay) => {
    timers.push(window.setTimeout(collapseSidebar, delay));
  });

  return () => {
    timers.forEach((timer) => window.clearTimeout(timer));
  };
}
"""


collapse_sidebar = st.components.v2.component(
    "collapse_sidebar",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
