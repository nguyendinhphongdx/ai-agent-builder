import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "AgentForge — open platform for production-ready AI agents";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function OG() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          padding: "80px",
          background:
            "linear-gradient(135deg, #0b1220 0%, #1e1b4b 50%, #4c1d95 100%)",
          color: "white",
          fontFamily: "system-ui, sans-serif",
          position: "relative",
        }}
      >
        {/* Brand */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "rgba(255,255,255,0.95)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: 26,
              color: "#4338ca",
            }}
          >
            ⌬
          </div>
          <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: -0.5 }}>
            AgentForge
          </div>
        </div>

        {/* Headline */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            marginTop: "auto",
            gap: 24,
          }}
        >
          <div
            style={{
              fontSize: 76,
              fontWeight: 800,
              letterSpacing: -2,
              lineHeight: 1.05,
            }}
          >
            Stop duct-taping
            <br />
            <span
              style={{
                background: "linear-gradient(90deg, #60a5fa, #c084fc)",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              LangChain scripts.
            </span>
          </div>

          <div
            style={{
              fontSize: 28,
              color: "rgba(255,255,255,0.7)",
              maxWidth: 900,
              lineHeight: 1.4,
            }}
          >
            Open platform for AI agents. Embed, REST, or MCP — your call.
          </div>
        </div>

        {/* Footer chips */}
        <div
          style={{
            display: "flex",
            gap: 12,
            marginTop: 40,
            fontSize: 18,
            color: "rgba(255,255,255,0.7)",
          }}
        >
          {["MIT licensed", "Self-hostable", "5 min setup"].map((t) => (
            <div
              key={t}
              style={{
                padding: "8px 16px",
                borderRadius: 999,
                border: "1px solid rgba(255,255,255,0.2)",
                background: "rgba(255,255,255,0.05)",
              }}
            >
              {t}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
