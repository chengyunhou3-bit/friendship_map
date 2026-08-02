import streamlit as st


COMPONENT_HTML = """
<div class="map-shell">
  <svg
    id="relationship-map"
    viewBox="0 0 700 620"
    role="img"
    aria-label="可拖曳的人際關係座標圖"
  >
    <rect class="plot-background" x="70" y="30" width="580" height="520"></rect>
    <g id="grid-layer"></g>
    <g id="point-layer"></g>
    <text id="x-axis-title" class="axis-title" x="360" y="603" text-anchor="middle">
      熟悉度：不熟 ← → 熟悉
    </text>
    <text
      id="y-axis-title"
      class="axis-title"
      x="18"
      y="290"
      text-anchor="middle"
      transform="rotate(-90 18 290)"
    >
      好感度：負面 ← → 喜歡
    </text>
  </svg>
  <div class="drag-controls">
    <button id="save-coordinates" class="save-coordinates" type="button" disabled>
      💾 儲存座標
    </button>
    <span id="save-status" class="save-status">拖曳後 30 秒自動儲存</span>
  </div>
</div>
"""


COMPONENT_CSS = """
.map-shell {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  padding: 0.5rem;
  border: 1px solid color-mix(in srgb, var(--st-text-color) 18%, transparent);
  border-radius: 1rem;
  background: var(--st-secondary-background-color);
}

#relationship-map {
  display: block;
  width: 100%;
  height: calc(100% - 4.25rem);
  min-height: 500px;
  touch-action: none;
  user-select: none;
}

.plot-background {
  fill: var(--st-background-color);
  stroke: color-mix(in srgb, var(--st-text-color) 25%, transparent);
}

.grid-line {
  stroke: color-mix(in srgb, var(--st-text-color) 13%, transparent);
  stroke-width: 1;
}

.zero-line {
  stroke: color-mix(in srgb, var(--st-text-color) 48%, transparent);
  stroke-width: 2;
}

.tick-label,
.axis-title,
.point-label {
  fill: var(--st-text-color);
  font-family: -apple-system, BlinkMacSystemFont, "PingFang TC", sans-serif;
}

.tick-label {
  font-size: 13px;
}

.axis-title {
  font-size: 16px;
  font-weight: 600;
}

.person-point {
  cursor: grab;
}

.person-point:active {
  cursor: grabbing;
}

.point-circle {
  fill: var(--st-primary-color);
  stroke: var(--st-background-color);
  stroke-width: 3;
  filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.22));
}

.person-point:hover .point-circle {
  stroke: var(--st-text-color);
  stroke-width: 4;
}

.point-label {
  font-size: 15px;
  font-weight: 700;
  pointer-events: none;
  paint-order: stroke;
  stroke: var(--st-background-color);
  stroke-width: 4px;
  stroke-linejoin: round;
}

.drag-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 0.35rem;
}

.save-coordinates {
  border: 0;
  border-radius: 0.55rem;
  padding: 0.55rem 1rem;
  color: white;
  background: var(--st-primary-color);
  font: inherit;
  font-weight: 650;
  cursor: pointer;
}

.save-coordinates:disabled {
  cursor: default;
  opacity: 0.45;
}

.save-status {
  color: color-mix(in srgb, var(--st-text-color) 70%, transparent);
  font-size: 0.9rem;
}

@media (max-width: 520px) {
  .drag-controls {
    align-items: stretch;
    flex-direction: column;
    gap: 0.3rem;
    text-align: center;
  }
}
"""


COMPONENT_JS = """
export default function(component) {
  const { data, parentElement, setTriggerValue } = component;
  const svg = parentElement.querySelector("#relationship-map");
  const gridLayer = parentElement.querySelector("#grid-layer");
  const pointLayer = parentElement.querySelector("#point-layer");
  const xAxisTitle = parentElement.querySelector("#x-axis-title");
  const yAxisTitle = parentElement.querySelector("#y-axis-title");
  const saveButton = parentElement.querySelector("#save-coordinates");
  const saveStatus = parentElement.querySelector("#save-status");
  const svgNamespace = "http://www.w3.org/2000/svg";

  const left = 70;
  const right = 650;
  const top = 30;
  const bottom = 550;
  const plotWidth = right - left;
  const plotHeight = bottom - top;
  const ticks = [-100, -50, 0, 50, 100];

  xAxisTitle.textContent = data?.axisTitles?.x
    || "熟悉度：不熟 ← → 熟悉";
  yAxisTitle.textContent = data?.axisTitles?.y
    || "好感度：負面 ← → 喜歡";

  const clamp = (value) => Math.max(-100, Math.min(100, value));
  const toPixelX = (value) => left + ((value + 100) / 200) * plotWidth;
  const toPixelY = (value) => bottom - ((value + 100) / 200) * plotHeight;
  const toValueX = (pixel) => clamp(Math.round(((pixel - left) / plotWidth) * 200 - 100));
  const toValueY = (pixel) => clamp(Math.round(((bottom - pixel) / plotHeight) * 200 - 100));

  const makeSvgElement = (tagName, attributes = {}) => {
    const element = document.createElementNS(svgNamespace, tagName);
    Object.entries(attributes).forEach(([key, value]) => {
      element.setAttribute(key, String(value));
    });
    return element;
  };

  gridLayer.replaceChildren();
  pointLayer.replaceChildren();

  ticks.forEach((tick) => {
    const x = toPixelX(tick);
    const y = toPixelY(tick);

    const verticalLine = makeSvgElement("line", {
      x1: x,
      y1: top,
      x2: x,
      y2: bottom,
      class: tick === 0 ? "zero-line" : "grid-line"
    });
    gridLayer.appendChild(verticalLine);

    const horizontalLine = makeSvgElement("line", {
      x1: left,
      y1: y,
      x2: right,
      y2: y,
      class: tick === 0 ? "zero-line" : "grid-line"
    });
    gridLayer.appendChild(horizontalLine);

    const xLabel = makeSvgElement("text", {
      x,
      y: bottom + 22,
      "text-anchor": "middle",
      class: "tick-label"
    });
    xLabel.textContent = tick;
    gridLayer.appendChild(xLabel);

    const yLabel = makeSvgElement("text", {
      x: left - 12,
      y: y + 5,
      "text-anchor": "end",
      class: "tick-label"
    });
    yLabel.textContent = tick;
    gridLayer.appendChild(yLabel);
  });

  const points = Array.isArray(data?.points)
    ? data.points
        .filter((point) =>
          typeof point?.name === "string"
          && Number.isFinite(Number(point?.x))
          && Number.isFinite(Number(point?.y))
        )
        .map((point) => ({
          name: point.name,
          x: clamp(Number(point.x)),
          y: clamp(Number(point.y))
        }))
    : [];

  const pointElements = new Map();
  const pendingMoves = new Map();
  let activePoint = null;
  let saveTimer = null;
  let lastMovementAt = 0;

  const cancelScheduledSave = () => {
    if (saveTimer === null) return;
    window.clearTimeout(saveTimer);
    saveTimer = null;
  };

  const flushPendingMoves = () => {
    cancelScheduledSave();
    if (pendingMoves.size === 0) return;

    const movedPoints = Array.from(pendingMoves.values());
    pendingMoves.clear();
    saveButton.disabled = true;
    saveStatus.textContent = "正在儲存…";
    setTriggerValue("moved", {
      points: movedPoints,
      eventId: `${Date.now()}`
    });
  };

  const scheduleSave = () => {
    if (pendingMoves.size === 0 || saveTimer !== null) return;

    const checkForIdle = () => {
      saveTimer = null;
      if (pendingMoves.size === 0) return;

      const remainingTime = 30000 - (Date.now() - lastMovementAt);
      if (remainingTime > 0) {
        saveTimer = window.setTimeout(checkForIdle, remainingTime);
        return;
      }

      flushPendingMoves();
    };

    saveTimer = window.setTimeout(checkForIdle, 30000);
  };

  const markPointAsPending = (point) => {
    lastMovementAt = Date.now();
    pendingMoves.set(point.name, {
      name: point.name,
      x: point.x,
      y: point.y
    });
    if (saveButton.disabled) {
      saveButton.disabled = false;
      saveStatus.textContent = "尚未儲存；停止拖曳 30 秒後自動儲存";
    }
    scheduleSave();
  };

  saveButton.onclick = flushPendingMoves;

  const movePointElement = (point) => {
    const group = pointElements.get(point.name);
    if (!group) return;
    group.setAttribute(
      "transform",
      `translate(${toPixelX(point.x)} ${toPixelY(point.y)})`
    );
  };

  points.forEach((point) => {
    const group = makeSvgElement("g", {
      class: "person-point",
      tabindex: "0",
      role: "button",
      "aria-label": `${point.name}，座標 ${point.x}, ${point.y}`
    });

    const circle = makeSvgElement("circle", {
      r: 12,
      class: "point-circle"
    });
    group.appendChild(circle);

    const label = makeSvgElement("text", {
      x: 17,
      y: -15,
      class: "point-label"
    });
    label.textContent = point.name;
    group.appendChild(label);

    group.onpointerdown = (event) => {
      event.preventDefault();
      cancelScheduledSave();
      activePoint = point;
      svg.setPointerCapture(event.pointerId);
    };

    pointElements.set(point.name, group);
    pointLayer.appendChild(group);
    movePointElement(point);
  });

  const eventToSvgPoint = (event) => {
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    return point.matrixTransform(svg.getScreenCTM().inverse());
  };

  svg.onpointermove = (event) => {
    if (!activePoint) return;

    const svgPoint = eventToSvgPoint(event);
    activePoint.x = toValueX(svgPoint.x);
    activePoint.y = toValueY(svgPoint.y);
    movePointElement(activePoint);
    markPointAsPending(activePoint);
  };

  const finishDrag = () => {
    if (!activePoint) return;

    markPointAsPending(activePoint);
    activePoint = null;
  };

  svg.onpointerup = finishDrag;
  svg.onpointercancel = () => {
    activePoint = null;
    scheduleSave();
  };

  return () => {
    cancelScheduledSave();
    saveButton.onclick = null;
    svg.onpointermove = null;
    svg.onpointerup = null;
    svg.onpointercancel = null;
  };
}
"""


draggable_relationship_map = st.components.v2.component(
    "draggable_relationship_map",
    html=COMPONENT_HTML,
    css=COMPONENT_CSS,
    js=COMPONENT_JS
)
