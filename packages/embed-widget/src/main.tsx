/**
 * Embed widget entry point. Two ways for sites to use it:
 *
 *   1. Auto-mount via script tag attributes:
 *        <script src="…/embed.js"
 *                data-token="afp_…"
 *                data-api="https://api.agentforge.ai/api"
 *                data-color="#2563eb"
 *                defer></script>
 *
 *   2. Programmatic via window.AgentForge:
 *        AgentForge.mount({ token, apiUrl, target?: HTMLElement, color? })
 *
 * Render target is a shadow root attached to a host <div>, so neither widget
 * styles nor host page styles bleed across.
 */
import { render } from "preact";
import { Widget } from "./Widget";
import { widgetStyles } from "./styles";

interface MountOptions {
  token: string;
  apiUrl?: string;
  target?: HTMLElement;
  color?: string;
}

const DEFAULT_API = "http://localhost:8000/api";
const DEFAULT_COLOR = "#2563eb";

function mount(opts: MountOptions): void {
  if (!opts.token) {
    console.error("[AgentForge] mount() requires a `token`");
    return;
  }

  // Create a host element if no explicit target — appended to <body>
  // so the widget can position itself fixed to the viewport.
  const host =
    opts.target ?? Object.assign(document.createElement("div"), {});
  if (!opts.target) {
    host.setAttribute("data-agentforge-host", "");
    document.body.appendChild(host);
  }

  // Shadow DOM isolates our CSS from the host site. The widget exclusively
  // queries within this root, so global selectors on the host can't leak.
  const shadow = host.attachShadow({ mode: "open" });
  const styleEl = document.createElement("style");
  styleEl.textContent = widgetStyles({ color: opts.color ?? DEFAULT_COLOR });
  shadow.appendChild(styleEl);

  const mountPoint = document.createElement("div");
  shadow.appendChild(mountPoint);

  render(
    <Widget
      apiUrl={opts.apiUrl ?? DEFAULT_API}
      shareToken={opts.token}
    />,
    mountPoint,
  );
}

// Auto-init from the script tag that loaded us. Look at the *current* script
// element's data-* attrs. document.currentScript may be null in some module
// contexts; fall back to scanning for the data-token attribute.
function autoInit(): void {
  let s: HTMLScriptElement | null =
    document.currentScript as HTMLScriptElement | null;
  if (!s || !s.dataset.token) {
    s = document.querySelector(
      "script[data-token][src*='embed.js']",
    ) as HTMLScriptElement | null;
  }
  if (!s) return;
  const token = s.dataset.token;
  if (!token) return;
  mount({
    token,
    apiUrl: s.dataset.api,
    color: s.dataset.color,
  });
}

// Expose programmatic API.
(window as unknown as { AgentForge: { mount: typeof mount } }).AgentForge = {
  mount,
};

// Defer auto-init until DOM ready so document.body exists.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", autoInit, { once: true });
} else {
  autoInit();
}
