/**
 * Widget styles as a single CSS string — injected into the shadow root so
 * we never collide with the host page's CSS. Resolves theme color from
 * the agent's share_settings.
 */
export function widgetStyles(theme: { color: string }): string {
  return `
:host {
  all: initial;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
}

*, *::before, *::after { box-sizing: border-box; }

.fab {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: ${theme.color};
  color: #fff;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0,0,0,.18);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2147483646;
  transition: transform .12s ease;
}
.fab:hover { transform: scale(1.05); }
.fab svg { width: 24px; height: 24px; fill: currentColor; }

.panel {
  position: fixed;
  bottom: 88px;
  right: 20px;
  width: 380px;
  max-width: calc(100vw - 40px);
  height: 560px;
  max-height: calc(100vh - 120px);
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0,0,0,.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  z-index: 2147483647;
}

.head {
  background: ${theme.color};
  color: #fff;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.head .avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: rgba(255,255,255,.25);
  flex: 0 0 auto;
  display: flex; align-items: center; justify-content: center;
  font-weight: 600; font-size: 13px;
  overflow: hidden;
}
.head .avatar img { width: 100%; height: 100%; object-fit: cover; }
.head .meta { flex: 1; min-width: 0; }
.head .name { font-weight: 600; font-size: 14px; line-height: 1.2; }
.head .desc {
  font-size: 11px; opacity: .85;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.head .close {
  background: none; border: none; color: #fff; cursor: pointer;
  padding: 4px; border-radius: 6px; opacity: .8;
}
.head .close:hover { opacity: 1; background: rgba(255,255,255,.15); }

.msgs {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  background: #f7f7f8;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.msg { max-width: 80%; padding: 9px 12px; border-radius: 14px; font-size: 13px; line-height: 1.45; word-wrap: break-word; white-space: pre-wrap; }
.msg.u { align-self: flex-end; background: ${theme.color}; color: #fff; border-bottom-right-radius: 4px; }
.msg.a { align-self: flex-start; background: #fff; color: #111; border: 1px solid #e5e5e7; border-bottom-left-radius: 4px; }
.msg.err { align-self: flex-start; background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.msg .cursor { display: inline-block; width: 6px; height: 14px; background: currentColor; margin-left: 2px; vertical-align: middle; animation: blink 1s steps(2) infinite; }
@keyframes blink { 50% { opacity: 0; } }

.foot {
  border-top: 1px solid #e5e5e7;
  background: #fff;
  padding: 10px;
  display: flex;
  gap: 8px;
}
.foot textarea {
  flex: 1;
  resize: none;
  border: 1px solid #e5e5e7;
  border-radius: 10px;
  padding: 9px 12px;
  font: inherit;
  font-size: 13px;
  outline: none;
  max-height: 100px;
  min-height: 38px;
}
.foot textarea:focus { border-color: ${theme.color}; }
.foot button {
  background: ${theme.color};
  color: #fff;
  border: none;
  width: 38px; height: 38px;
  border-radius: 10px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex: 0 0 auto;
}
.foot button:disabled { opacity: .5; cursor: not-allowed; }
.foot button svg { width: 16px; height: 16px; fill: #fff; }

.brand {
  text-align: center;
  font-size: 10px;
  color: #9ca3af;
  padding: 6px 0 8px;
  background: #fff;
}
.brand a { color: inherit; text-decoration: none; }
.brand a:hover { text-decoration: underline; }
`;
}
