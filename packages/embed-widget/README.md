# lc-agent-embed

Drop-in chat widget that lets any website embed an AgentForge agent.

## Usage

**Script tag (auto-mount):**

```html
<script
  src="https://cdn.agentforge.ai/embed.js"
  data-token="<share_token>"
  data-api="https://api.agentforge.ai/api"
  data-color="#2563eb"
  defer
></script>
```

**Programmatic:**

```html
<script src="https://cdn.agentforge.ai/embed.js" defer></script>
<script>
  AgentForge.mount({
    token: "<share_token>",
    apiUrl: "https://api.agentforge.ai/api",
    color: "#2563eb",
    // target: document.getElementById("my-chat-slot"), // optional inline mount
  });
</script>
```

## Build

```bash
pnpm install
pnpm build   # → dist/embed.js
```

The output is a single self-contained IIFE — no module loader required on the
host page. CSS is injected into a shadow root so neither the host page's
styles nor ours leak across.
